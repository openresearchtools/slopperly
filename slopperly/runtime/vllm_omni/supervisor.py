"""vLLM-Omni process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .tts_client import VllmOmniTtsClient


class VllmOmniSupervisor:
    def __init__(self, venv: str | Path = ".slopperly/vllm-omni-venv", url: str = "http://127.0.0.1:8091"):
        self.venv = Path(venv)
        self.url = url

    def health(self) -> dict:
        return VllmOmniTtsClient(self.url).health()

    def launch_command(self, model: str) -> list[str]:
        port = self.url.rsplit(":", 1)[-1]
        return [
            str(self.venv / "bin" / "python"),
            "-m",
            "vllm_omni.entrypoints.openai.api_server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--model",
            model,
        ]

    def start(self, model: str) -> subprocess.Popen:
        return subprocess.Popen(self.launch_command(model))
