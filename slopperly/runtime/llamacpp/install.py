"""Installer recipe for the requested llama.cpp Ubuntu x64 CUDA artifact."""

from __future__ import annotations

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Slopperly llama.cpp runtime")
    parser.add_argument("--runtime-root", default=".slopperly/runtimes")
    parser.add_argument("--release", default="b9803")
    parser.add_argument("--artifact", default="ubuntu-x64-cuda13")
    args = parser.parse_args(argv)
    root = Path(args.runtime_root) / "llama.cpp"
    root.mkdir(parents=True, exist_ok=True)
    print(f"llama.cpp release: {args.release}")
    print(f"artifact: {args.artifact}")
    print(f"install target: {root}")
    print("Download/extract the pinned CUDA artifact here, then run slopperly doctor to verify launch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
