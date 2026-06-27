"""Installer entry point for the Slopperly-owned ComfyUI runtime."""

from __future__ import annotations

import argparse
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
        dry_run=args.dry_run,
        skip_pip=args.skip_pip,
        force=args.force,
    )
    print_steps(steps, title="ComfyUI install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
