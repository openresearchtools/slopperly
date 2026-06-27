"""vLLM process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .stt_client import VllmSttClient


class VllmSupervisor:
    def __init__(self, venv: str | Path = ".slopperly/vllm-venv", url: str = "http://127.0.0.1:8090"):
        self.venv = Path(venv)
        self.url = url

    def health(self) -> dict:
        return VllmSttClient(self.url).health()

    def launch_command(self, model: str = "openai/whisper-large-v3-turbo") -> list[str]:
        port = self.url.rsplit(":", 1)[-1]
        return [
            str(self.venv / "bin" / "python"),
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--model",
            model,
        ]

    def start(self, model: str = "openai/whisper-large-v3-turbo") -> subprocess.Popen:
        return subprocess.Popen(self.launch_command(model))
