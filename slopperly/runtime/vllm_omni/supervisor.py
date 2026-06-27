"""vLLM-Omni process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.supervisor_utils import (
    executable_check,
    local_host_port,
    require_preflight,
)

from .tts_client import VllmOmniTtsClient


class VllmOmniSupervisor:
    def __init__(self, venv: str | Path = ".slopperly/vllm-omni-venv", url: str = "http://127.0.0.1:8091"):
        self.venv = Path(venv)
        self.url = url

    def health(self) -> dict:
        return VllmOmniTtsClient(self.url).health()

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    def launch_command(self, model: str) -> list[str]:
        host, port = local_host_port(self.url, default_port=8091, label="vLLM-Omni")
        return [
            str(self.python),
            "-m",
            "vllm_omni.entrypoints.openai.api_server",
            "--host",
            host,
            "--port",
            str(port),
            "--model",
            model,
        ]

    def preflight(self) -> list[InstallStep]:
        return [executable_check(self.python, name="python")]

    def start(self, model: str) -> subprocess.Popen:
        require_preflight(self.preflight())
        return subprocess.Popen(self.launch_command(model))
