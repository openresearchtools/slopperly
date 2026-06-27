"""Installer recipe for the Slopperly vLLM-Omni runtime venv."""

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


def install_vllm_omni(
    *,
    venv_dir: Path,
    dry_run: bool = False,
    skip_pip: bool = False,
) -> list[InstallStep]:
    steps = [create_venv(venv_dir, dry_run=dry_run)]
    if not skip_pip:
        steps.append(pip_install(venv_pip(venv_dir), ["vllm-omni"], dry_run=dry_run))
    steps.append(
        write_manifest(
            venv_dir.parent / "vllm-omni-install-manifest.json",
            {
                "runtime": "vllm_omni",
                "venv": str(venv_dir),
                "package": "vllm-omni",
            },
            dry_run=dry_run,
        )
    )
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/install Slopperly vLLM-Omni venv")
    parser.add_argument("--venv", default=".slopperly/vllm-omni-venv")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    steps = install_vllm_omni(
        venv_dir=Path(args.venv),
        dry_run=args.dry_run,
        skip_pip=args.skip_pip,
    )
    print_steps(steps, title="vLLM-Omni install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
