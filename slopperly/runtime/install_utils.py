"""Shared helpers for Slopperly local runtime installers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import venv
from pathlib import Path


@dataclass(frozen=True)
class InstallStep:
    status: str
    name: str
    detail: str


def print_steps(steps: list[InstallStep], *, title: str) -> None:
    for step in steps:
        print(f"{step.status} {step.name}: {step.detail}")
    counts = {
        status: sum(1 for step in steps if step.status == status)
        for status in {"PASS", "PLAN", "BLOCKED"}
    }
    print(
        f"{title}: {counts['PASS']} passed, "
        f"{counts['PLAN']} planned, {counts['BLOCKED']} blocked."
    )


def has_blockers(steps: list[InstallStep]) -> bool:
    return any(step.status == "BLOCKED" for step in steps)


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
) -> InstallStep:
    label = command[0] if command else "command"
    printable = " ".join(command)
    if dry_run:
        return InstallStep("PLAN", label, printable)
    try:
        subprocess.check_call(command, cwd=str(cwd) if cwd else None)
    except FileNotFoundError as exc:
        return InstallStep("BLOCKED", label, f"missing executable: {exc.filename}")
    except subprocess.CalledProcessError as exc:
        return InstallStep("BLOCKED", label, f"{printable} exited {exc.returncode}")
    return InstallStep("PASS", label, printable)


def create_venv(venv_dir: Path, *, dry_run: bool = False) -> InstallStep:
    if dry_run:
        return InstallStep("PLAN", "venv", f"create {venv_dir}")
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    return InstallStep("PASS", "venv", f"ready {venv_dir}")


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_pip(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")


def git_checkout(
    *,
    repo: str,
    commit: str,
    destination: Path,
    dry_run: bool = False,
    force: bool = False,
) -> list[InstallStep]:
    steps: list[InstallStep] = []
    if not repo or not commit:
        return [InstallStep("BLOCKED", destination.name, "repo and commit are required")]
    if destination.exists() and not (destination / ".git").is_dir():
        if not force:
            return [
                InstallStep(
                    "BLOCKED",
                    destination.name,
                    f"{destination} exists but is not a git checkout; pass --force to replace it",
                )
            ]
        if dry_run:
            steps.append(InstallStep("PLAN", destination.name, f"remove {destination}"))
        else:
            shutil.rmtree(destination)

    if not destination.exists():
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
        steps.append(
            run_command(
                ["git", "clone", "--filter=blob:none", repo, str(destination)],
                dry_run=dry_run,
            )
        )
    else:
        steps.append(
            run_command(["git", "-C", str(destination), "fetch", "--tags", "origin"], dry_run=dry_run)
        )
    steps.append(
        run_command(
            ["git", "-C", str(destination), "checkout", "--detach", commit],
            dry_run=dry_run,
        )
    )
    return steps


def pip_install(
    pip: Path,
    args: list[str],
    *,
    dry_run: bool = False,
) -> InstallStep:
    return run_command([str(pip), "install", *args], dry_run=dry_run)


def write_manifest(path: Path, payload: dict, *, dry_run: bool = False) -> InstallStep:
    if dry_run:
        return InstallStep("PLAN", "manifest", f"write {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return InstallStep("PASS", "manifest", f"wrote {path}")


def download_file(url: str, destination: Path, *, dry_run: bool = False) -> InstallStep:
    if dry_run:
        return InstallStep("PLAN", "download", f"{url} -> {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())
    except Exception as exc:
        return InstallStep("BLOCKED", "download", f"{url}: {exc}")
    return InstallStep("PASS", "download", f"wrote {destination}")


def current_python() -> str:
    return sys.executable or "python"
