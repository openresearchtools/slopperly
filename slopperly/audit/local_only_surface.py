"""Audit that the old Palladium remote backend surface is not production code."""

from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN_PATHS = (
    "remote_backends",
    "models/remote_base.py",
    "utils/remote_backend.py",
    "utils/adapter_launcher.py",
    "test_remote_backend.py",
)

FORBIDDEN_PATTERNS = (
    "register_remote_models",
    "clear_remote_models",
    "RemoteModelPlugin",
    "make_remote_plugin",
    "client_from_prefs",
    "save_discovery_cache",
    "load_discovery_cache",
    "remote_backend_url",
    "remote_backend_key",
    "PALLAIDIUM_BACKEND_URL",
    "PALLAIDIUM_BACKEND_KEY",
    "remote_generate_audio",
    "InputSpec.API_KEY",
    "InputSpec.HF_TOKEN",
)

SCAN_ROOTS = (
    "__init__.py",
    "blender_manifest.toml",
    "models",
    "models_plugins",
    "operators",
    "properties",
    "ui",
    "utils",
    "slopperly",
)

ALLOWLIST_PREFIXES = (
    "reference/",
    "docs/",
    "README.md",
    "AGENTS.md",
    "unsupported_models_plugins/",
    "slopperly/audit/local_only_surface.py",
)


def iter_scan_files(root: Path):
    for rel_root in SCAN_ROOTS:
        path = root / rel_root
        if not path.exists():
            continue
        if path.is_file():
            yield path, path.relative_to(root).as_posix()
            continue
        for child in path.rglob("*"):
            if not child.is_file() or ".git" in child.parts:
                continue
            rel = child.relative_to(root).as_posix()
            if rel.startswith(ALLOWLIST_PREFIXES):
                continue
            yield child, rel


def audit(root: Path) -> list[str]:
    failures: list[str] = []
    for rel in FORBIDDEN_PATHS:
        if (root / rel).exists():
            failures.append(f"forbidden production path exists: {rel}")

    for path, rel in iter_scan_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    failures.append(f"{rel}:{lineno}: forbidden remote surface {pattern!r}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if legacy remote backend production surface remains")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    failures = audit(root)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("No production remote backend surface found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
