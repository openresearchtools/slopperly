"""Installer recipe for the Slopperly vLLM-Omni runtime venv."""

from __future__ import annotations

import argparse
import subprocess
import venv
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/install Slopperly vLLM-Omni venv")
    parser.add_argument("--venv", default=".slopperly/vllm-omni-venv")
    parser.add_argument("--skip-pip", action="store_true")
    args = parser.parse_args(argv)
    venv_dir = Path(args.venv)
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    if not args.skip_pip:
        pip = venv_dir / "bin" / "pip"
        subprocess.check_call([str(pip), "install", "vllm-omni"])
    print(f"vLLM-Omni venv ready: {venv_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
