"""Installer entry point for the Slopperly-owned ComfyUI runtime."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from slopperly.config.registry import load_yaml
from slopperly.runtime.install_utils import (
    InstallStep,
    create_venv,
    git_checkout,
    has_blockers,
    pip_install,
    print_steps,
    venv_pip,
    write_manifest,
)


def install_comfy(
    *,
    runtime_root: Path,
    pin: Path,
    profile: str,
    dry_run: bool = False,
    skip_pip: bool = False,
    force: bool = False,
) -> list[InstallStep]:
    lock = load_yaml(pin)
    comfy = lock.get("comfyui") if isinstance(lock, dict) else None
    nodes = lock.get("custom_nodes") if isinstance(lock, dict) else None
    if not isinstance(comfy, dict) or not isinstance(nodes, list):
        return [InstallStep("BLOCKED", "nodes.lock", f"invalid lock file: {pin}")]

    runtime_root = runtime_root.resolve()
    comfy_path = runtime_root / "ComfyUI"
    venv_dir = runtime_root / "comfy-venv"
    pip = venv_pip(venv_dir)
    steps: list[InstallStep] = [
        InstallStep("PLAN" if dry_run else "PASS", "profile", f"ComfyUI install profile {profile}")
    ]
    steps.extend(
        git_checkout(
            repo=str(comfy.get("repo", "")),
            commit=str(comfy.get("commit", "")),
            destination=comfy_path,
            dry_run=dry_run,
            force=force,
        )
    )
    steps.append(create_venv(venv_dir, dry_run=dry_run))
    if not skip_pip:
        steps.extend(install_python_requirements(comfy_path, comfy, pip, dry_run=dry_run))

    custom_nodes_dir = comfy_path / "custom_nodes"
    for node in nodes:
        if not isinstance(node, dict):
            steps.append(InstallStep("BLOCKED", "custom_nodes", f"invalid node entry: {node!r}"))
            continue
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            steps.append(InstallStep("BLOCKED", "custom_nodes", "node id is required"))
            continue
        node_path = custom_nodes_dir / node_id
        if str(node.get("source") or "git").strip().lower() == "local":
            steps.extend(
                install_local_custom_node(
                    node=node,
                    destination=node_path,
                    pin=pin,
                    dry_run=dry_run,
                    force=force,
                )
            )
        else:
            steps.extend(
                git_checkout(
                    repo=str(node.get("repo", "")),
                    commit=str(node.get("commit", "")),
                    destination=node_path,
                    dry_run=dry_run,
                    force=force,
                )
            )
        if not skip_pip:
            steps.extend(install_python_requirements(node_path, node, pip, dry_run=dry_run))

    steps.extend(apply_slopperly_post_install_patches(comfy_path, dry_run=dry_run))

    steps.append(
        write_manifest(
            runtime_root / "install-manifest.json",
            {
                "runtime": "comfyui",
                "profile": profile,
                "pin": str(pin),
                "comfyui": comfy,
                "custom_nodes": nodes,
                "runtime_path": str(comfy_path),
                "venv": str(venv_dir),
            },
            dry_run=dry_run,
        )
    )
    return steps


def apply_slopperly_post_install_patches(comfy_path: Path, *, dry_run: bool) -> list[InstallStep]:
    """Patch third-party nodes that perform network work during object_info."""

    return [
        disable_foundation1_object_info_autodownload(
            comfy_path / "custom_nodes" / "foundation_1" / "nodes" / "loader_node.py",
            dry_run=dry_run,
        )
    ]


def disable_foundation1_object_info_autodownload(path: Path, *, dry_run: bool) -> InstallStep:
    marker = "Slopperly disables upstream auto-download"
    if dry_run:
        return InstallStep(
            "PLAN",
            "foundation_1",
            f"patch {path} to keep /object_info local-only",
        )
    if not path.is_file():
        return InstallStep(
            "PASS",
            "foundation_1",
            f"Foundation-1 loader not present at {path}; no local-only patch needed",
        )
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return InstallStep(
            "PASS",
            "foundation_1",
            f"Foundation-1 object_info auto-download patch already present in {path}",
        )
    old = """        else:
            logger.info(
                "No Foundation-1 models found in models/stable_audio/. "
                "Attempting auto-download from HuggingFace..."
            )
            _download_foundation1()
            results = _do_scan()
"""
    new = """        else:
            logger.warning(
                "No Foundation-1 models found in models/stable_audio/. "
                "Slopperly disables upstream auto-download during /object_info "
                "and generation. Run python -m slopperly.models.download "
                "--model foundation1_music_loop --accept-licenses before "
                "certifying this workflow."
            )
"""
    if old not in text:
        return InstallStep(
            "BLOCKED",
            "foundation_1",
            f"could not find Foundation-1 auto-download block to patch in {path}",
        )
    path.write_text(text.replace(old, new), encoding="utf-8")
    return InstallStep(
        "PASS",
        "foundation_1",
        f"patched {path} to keep /object_info local-only",
    )


def install_local_custom_node(
    *,
    node: dict,
    destination: Path,
    pin: Path,
    dry_run: bool,
    force: bool,
) -> list[InstallStep]:
    source = resolve_local_node_path(str(node.get("path") or ""), pin=pin)
    if source is None:
        return [InstallStep("BLOCKED", destination.name, "local node path is required")]
    if not source.is_dir():
        return [InstallStep("BLOCKED", destination.name, f"local node path does not exist: {source}")]
    if destination.exists():
        if not force:
            return [InstallStep("PASS", destination.name, f"local node already installed at {destination}")]
        if dry_run:
            return [
                InstallStep("PLAN", destination.name, f"remove {destination}"),
                InstallStep("PLAN", destination.name, f"copy {source} -> {destination}"),
            ]
        shutil.rmtree(destination)
    if dry_run:
        return [InstallStep("PLAN", destination.name, f"copy {source} -> {destination}")]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return [InstallStep("PASS", destination.name, f"copied {source} -> {destination}")]


def resolve_local_node_path(raw_path: str, *, pin: Path) -> Path | None:
    text = raw_path.strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path.resolve()

    candidates = [Path.cwd() / path, pin.resolve().parent / path]
    try:
        candidates.append(pin.resolve().parents[3] / path)
    except IndexError:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (Path.cwd() / path).resolve()


def install_python_requirements(
    checkout: Path,
    recipe: dict,
    pip: Path,
    *,
    dry_run: bool,
) -> list[InstallStep]:
    steps: list[InstallStep] = []
    install_command = str(recipe.get("install_command") or "").strip()
    extras = recipe.get("python_extras") or []
    if install_command == "pip install -r requirements.txt":
        requirements = checkout / "requirements.txt"
        if dry_run or requirements.exists():
            steps.append(pip_install(pip, ["-r", str(requirements)], dry_run=dry_run))
        else:
            steps.append(
                InstallStep(
                    "PASS",
                    checkout.name,
                    f"no requirements.txt present at {requirements}; nothing to install",
                )
            )
    elif install_command:
        steps.append(
            InstallStep(
                "BLOCKED",
                checkout.name,
                f"unsupported install_command {install_command!r}; only pip requirements are allowed",
            )
        )
    if not isinstance(extras, list):
        steps.append(InstallStep("BLOCKED", checkout.name, "python_extras must be a list"))
    else:
        for package in extras:
            steps.append(pip_install(pip, [str(package)], dry_run=dry_run))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Slopperly-owned ComfyUI")
    parser.add_argument("--runtime-root", default=".slopperly/runtimes")
    parser.add_argument("--pin", default="slopperly/runtime/comfy/nodes.lock.yaml")
    parser.add_argument("--profile", default="cuda13")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    steps = install_comfy(
        runtime_root=Path(args.runtime_root),
        pin=Path(args.pin),
        profile=args.profile,
        dry_run=args.dry_run or args.report_only,
        skip_pip=args.skip_pip,
        force=args.force,
    )
    print_steps(steps, title="ComfyUI install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
