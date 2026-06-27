"""llama.cpp process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .client import LlamaCppClient


class LlamaCppSupervisor:
    def __init__(self, runtime_root: str | Path, url: str = "http://127.0.0.1:8092"):
        self.runtime_root = Path(runtime_root)
        self.url = url

    def health(self) -> dict:
        return LlamaCppClient(self.url).health()

    def launch_command(self, model_path: str, *, context_length: int = 60000) -> list[str]:
        binary = self.runtime_root / "llama.cpp" / "llama-server"
        port = self.url.rsplit(":", 1)[-1]
        return [
            str(binary),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--model",
            model_path,
            "--ctx-size",
            str(context_length),
        ]

    def start(self, model_path: str) -> subprocess.Popen:
        cmd = self.launch_command(model_path)
        return subprocess.Popen(cmd, cwd=str(self.runtime_root / "llama.cpp"))
