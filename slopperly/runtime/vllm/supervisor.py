"""vLLM process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.supervisor_utils import (
    executable_check,
    local_host_port,
    require_preflight,
)

from .stt_client import VllmSttClient


class VllmSupervisor:
    def __init__(self, venv: str | Path = ".slopperly/vllm-venv", url: str = "http://127.0.0.1:8090"):
        self.venv = Path(venv)
        self.url = url

    def health(self) -> dict:
        return VllmSttClient(self.url).health()

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    def launch_command(self, model: str = "openai/whisper-large-v3-turbo") -> list[str]:
        host, port = local_host_port(self.url, default_port=8090, label="vLLM")
        return [
            str(self.python),
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--host",
            host,
            "--port",
            str(port),
            "--model",
            model,
        ]

    def preflight(self) -> list[InstallStep]:
        return [executable_check(self.python, name="python")]

    def start(self, model: str = "openai/whisper-large-v3-turbo") -> subprocess.Popen:
        require_preflight(self.preflight())
        return subprocess.Popen(self.launch_command(model))
