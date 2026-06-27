"""Installer entry point for the Slopperly-owned ComfyUI runtime."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Slopperly-owned ComfyUI")
    parser.add_argument("--runtime-root", default=".slopperly/runtimes")
    parser.add_argument("--pin", default="slopperly/runtime/comfy/nodes.lock.yaml")
    parser.add_argument("--profile", default="cuda13")
    args = parser.parse_args(argv)

    runtime_root = Path(args.runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    print(f"Runtime root: {runtime_root}")
    print(f"Node lock: {args.pin}")
    print(f"Profile: {args.profile}")
    print("Install recipe is pinned in nodes.lock.yaml; run from a networked shell to clone and install nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
