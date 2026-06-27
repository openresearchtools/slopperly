"""Shared launch helpers for local runtime supervisors."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.local_url import assert_local_http_url


def local_host_port(url: str, *, default_port: int, label: str) -> tuple[str, int]:
    normalized = assert_local_http_url(url, label=label)
    parsed = urlparse(normalized)
    return parsed.hostname or "127.0.0.1", parsed.port or default_port


def executable_check(path: Path, *, name: str) -> InstallStep:
    if not path.exists():
        return InstallStep("BLOCKED", name, f"missing executable: {path}")
    if not os.access(path, os.X_OK):
        return InstallStep("BLOCKED", name, f"not executable: {path}")
    return InstallStep("PASS", name, f"found {path}")


def file_check(path: Path, *, name: str) -> InstallStep:
    if not path.is_file():
        return InstallStep("BLOCKED", name, f"missing file: {path}")
    return InstallStep("PASS", name, f"found {path}")


def dir_check(path: Path, *, name: str) -> InstallStep:
    if not path.is_dir():
        return InstallStep("BLOCKED", name, f"missing directory: {path}")
    return InstallStep("PASS", name, f"found {path}")


def require_preflight(steps: list[InstallStep]) -> None:
    blockers = [step for step in steps if step.status == "BLOCKED"]
    if blockers:
        detail = "; ".join(f"{step.name}: {step.detail}" for step in blockers)
        raise RuntimeUnavailableError(detail)
