"""Installer recipe for the requested llama.cpp Ubuntu x64 CUDA artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from slopperly.runtime.install_utils import (
    InstallStep,
    download_file,
    has_blockers,
    print_steps,
    write_manifest,
)

RELEASE_API = "https://api.github.com/repos/openresearchtools/llama-cpp-arm64-builds/releases/tags"
SERVER_NAMES = {"llama-server", "llama-server.exe", "server", "server.exe"}


def release_api_url(release: str) -> str:
    return f"{RELEASE_API}/{urllib.parse.quote(release)}"


def select_release_asset(release_data: dict, artifact: str) -> dict | None:
    assets = release_data.get("assets")
    if not isinstance(assets, list):
        return None
    wanted = normalize_asset_name(artifact)
    wanted_tokens = [token for token in wanted.split("-") if token]
    matches = [
        asset for asset in assets
        if asset_matches(normalize_asset_name(str(asset.get("name", ""))), wanted, wanted_tokens)
    ]
    if not matches:
        return None
    archive_matches = [
        asset for asset in matches
        if str(asset.get("name", "")).endswith((".zip", ".tar.gz", ".tgz", ".tar.xz"))
    ]
    return archive_matches[0] if archive_matches else matches[0]


def normalize_asset_name(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


def asset_matches(normalized_name: str, wanted: str, wanted_tokens: list[str]) -> bool:
    if wanted in normalized_name:
        return True
    name_tokens = {token for token in normalized_name.split("-") if token}
    return bool(wanted_tokens) and all(token in name_tokens for token in wanted_tokens)


def fetch_release_asset_url(release: str, artifact: str) -> tuple[str | None, str]:
    url = release_api_url(release)
    with urllib.request.urlopen(url, timeout=60) as response:
        release_data = json.loads(response.read().decode("utf-8"))
    asset = select_release_asset(release_data, artifact)
    if not asset:
        return None, f"no release asset matching {artifact!r} in {url}"
    download_url = asset.get("browser_download_url")
    if not download_url:
        return None, f"matching release asset has no browser_download_url: {asset!r}"
    return str(download_url), str(asset.get("name") or artifact)


def install_llamacpp(
    *,
    runtime_root: Path,
    release: str,
    artifact: str,
    download_url: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    skip_launch_check: bool = False,
) -> list[InstallStep]:
    runtime_root = runtime_root.resolve()
    target = runtime_root / "llama.cpp"
    downloads = runtime_root / "downloads"
    steps: list[InstallStep] = [check_cuda_requirement(artifact, dry_run=dry_run)]
    asset_name = archive_name(download_url or artifact)

    if not download_url:
        api_url = release_api_url(release)
        if dry_run:
            steps.append(InstallStep("PLAN", "release", f"query {api_url} for {artifact}"))
            steps.append(InstallStep("PLAN", "download", f"download selected {artifact} asset"))
            steps.append(InstallStep("PLAN", "extract", f"extract selected asset into {target}"))
            steps.append(launch_step(target, dry_run=True, skip_launch_check=skip_launch_check))
            steps.append(manifest_step(runtime_root, release, artifact, None, dry_run=True))
            return steps
        try:
            download_url, asset_name = fetch_release_asset_url(release, artifact)
        except Exception as exc:
            steps.append(InstallStep("BLOCKED", "release", f"{api_url}: {exc}"))
            return steps
        if not download_url:
            steps.append(InstallStep("BLOCKED", "release", asset_name))
            return steps

    archive = downloads / archive_name(asset_name or download_url)
    if target.exists() and any(target.iterdir()):
        if not force:
            steps.append(
                InstallStep(
                    "BLOCKED",
                    "target",
                    f"{target} is not empty; pass --force to replace the llama.cpp runtime",
                )
            )
            return steps
        if dry_run:
            steps.append(InstallStep("PLAN", "target", f"remove {target}"))
        else:
            shutil.rmtree(target)

    steps.append(download_file(download_url, archive, dry_run=dry_run))
    steps.append(extract_archive(archive, target, dry_run=dry_run))
    steps.append(launch_step(target, dry_run=dry_run, skip_launch_check=skip_launch_check))
    steps.append(manifest_step(runtime_root, release, artifact, download_url, dry_run=dry_run))
    return steps


def check_cuda_requirement(artifact: str, *, dry_run: bool) -> InstallStep:
    if "cuda" not in artifact.lower():
        return InstallStep("PASS", "cuda", f"artifact {artifact} does not require CUDA")
    if dry_run:
        return InstallStep("PLAN", "cuda", "verify nvidia-smi before claiming CUDA runtime")
    try:
        output = subprocess.check_output(["nvidia-smi", "-L"], text=True, timeout=10).strip()
    except FileNotFoundError:
        return InstallStep("BLOCKED", "cuda", "nvidia-smi is not installed or not on PATH")
    except subprocess.CalledProcessError as exc:
        return InstallStep("BLOCKED", "cuda", f"nvidia-smi failed: {exc}")
    except subprocess.TimeoutExpired:
        return InstallStep("BLOCKED", "cuda", "nvidia-smi timed out")
    if not output:
        return InstallStep("BLOCKED", "cuda", "nvidia-smi reported no GPUs")
    return InstallStep("PASS", "cuda", output.splitlines()[0])


def archive_name(value: str) -> str:
    path = urllib.parse.urlparse(value).path
    name = Path(path).name if path else value
    return name or "llama.cpp-runtime.tar.gz"


def extract_archive(archive: Path, target: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep("PLAN", "extract", f"{archive} -> {target}")
    target.mkdir(parents=True, exist_ok=True)
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                safe_zip_extract(zf, target)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive) as tf:
                safe_tar_extract(tf, target)
        else:
            return InstallStep("BLOCKED", "extract", f"unsupported archive format: {archive}")
    except Exception as exc:
        return InstallStep("BLOCKED", "extract", f"{archive}: {exc}")
    return InstallStep("PASS", "extract", f"extracted {archive} into {target}")


def safe_zip_extract(zf: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for member in zf.namelist():
        destination = (target / member).resolve()
        if not destination.is_relative_to(root):
            raise ValueError(f"archive member escapes target: {member}")
    zf.extractall(target)


def safe_tar_extract(tf: tarfile.TarFile, target: Path) -> None:
    root = target.resolve()
    for member in tf.getmembers():
        destination = (target / member.name).resolve()
        if not destination.is_relative_to(root):
            raise ValueError(f"archive member escapes target: {member.name}")
    tf.extractall(target)


def find_server_binary(target: Path) -> Path | None:
    if not target.exists():
        return None
    for path in target.rglob("*"):
        if path.name in SERVER_NAMES and path.is_file():
            return path
    return None


def launch_step(target: Path, *, dry_run: bool, skip_launch_check: bool) -> InstallStep:
    if skip_launch_check:
        return InstallStep(
            "BLOCKED",
            "launch",
            "launch check skipped; llama.cpp CUDA runtime is not verified",
        )
    if dry_run:
        return InstallStep("PLAN", "launch", f"run llama-server --help under {target}")
    binary = find_server_binary(target)
    if not binary:
        return InstallStep("BLOCKED", "launch", f"no llama-server binary found under {target}")
    binary.chmod(binary.stat().st_mode | 0o111)
    try:
        subprocess.run([str(binary), "--help"], check=True, timeout=30, capture_output=True)
    except subprocess.CalledProcessError as exc:
        return InstallStep("BLOCKED", "launch", f"{binary} --help exited {exc.returncode}")
    except subprocess.TimeoutExpired:
        return InstallStep("BLOCKED", "launch", f"{binary} --help timed out")
    except OSError as exc:
        return InstallStep("BLOCKED", "launch", f"{binary}: {exc}")
    return InstallStep("PASS", "launch", f"{binary} launched with --help")


def manifest_step(
    runtime_root: Path,
    release: str,
    artifact: str,
    download_url: str | None,
    *,
    dry_run: bool,
) -> InstallStep:
    return write_manifest(
        runtime_root / "llamacpp-install-manifest.json",
        {
            "runtime": "llamacpp",
            "release": release,
            "artifact": artifact,
            "download_url": download_url,
            "target": str(runtime_root / "llama.cpp"),
            "launch_check": "llama-server --help",
        },
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Slopperly llama.cpp runtime")
    parser.add_argument("--runtime-root", default=".slopperly/runtimes")
    parser.add_argument("--release", default="b9803")
    parser.add_argument("--artifact", default="ubuntu-x64-cuda13")
    parser.add_argument("--download-url")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-launch-check", action="store_true")
    args = parser.parse_args(argv)

    steps = install_llamacpp(
        runtime_root=Path(args.runtime_root),
        release=args.release,
        artifact=args.artifact,
        download_url=args.download_url,
        dry_run=args.dry_run,
        force=args.force,
        skip_launch_check=args.skip_launch_check,
    )
    print_steps(steps, title="llama.cpp install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
