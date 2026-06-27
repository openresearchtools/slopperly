"""Installer recipe for the Slopperly vLLM runtime venv."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopperly.runtime.install_utils import (
    InstallStep,
    create_venv,
    has_blockers,
    pip_install,
    print_steps,
    venv_pip,
    write_manifest,
)


def install_vllm(
    *,
    venv_dir: Path,
    extras: str,
    dry_run: bool = False,
    skip_pip: bool = False,
) -> list[InstallStep]:
    package = "vllm"
    if extras:
        package = f"vllm[{extras}]"
    steps = [create_venv(venv_dir, dry_run=dry_run)]
    if not skip_pip:
        steps.append(pip_install(venv_pip(venv_dir), [package], dry_run=dry_run))
    steps.append(
        write_manifest(
            venv_dir.parent / "vllm-install-manifest.json",
            {
                "runtime": "vllm",
                "venv": str(venv_dir),
                "package": package,
                "extras": extras,
            },
            dry_run=dry_run,
        )
    )
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/install Slopperly vLLM venv")
    parser.add_argument("--venv", default=".slopperly/vllm-venv")
    parser.add_argument("--extras", default="audio")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    steps = install_vllm(
        venv_dir=Path(args.venv),
        extras=args.extras,
        dry_run=args.dry_run,
        skip_pip=args.skip_pip,
    )
    print_steps(steps, title="vLLM install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
