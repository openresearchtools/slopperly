"""Owned ComfyUI runtime health and launch helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .api_client import ComfyApiClient


class ComfySupervisor:
    def __init__(self, runtime_root: str | Path, url: str = "http://127.0.0.1:8188"):
        self.runtime_root = Path(runtime_root)
        self.url = url

    def health(self) -> dict:
        client = ComfyApiClient(self.url)
        return {"object_info_count": len(client.object_info())}

    def launch_command(self) -> list[str]:
        comfy_root = self.runtime_root / "ComfyUI"
        return [
            str(comfy_root / ".venv" / "bin" / "python"),
            "main.py",
            "--listen",
            "127.0.0.1",
            "--port",
            self.url.rsplit(":", 1)[-1],
        ]

    def start(self) -> subprocess.Popen:
        cmd = self.launch_command()
        return subprocess.Popen(cmd, cwd=str(self.runtime_root / "ComfyUI"))
