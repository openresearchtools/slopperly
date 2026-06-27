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
    def __init__(
        self,
        venv: str | Path = ".slopperly/vllm-omni-venv",
        url: str = "http://127.0.0.1:8091",
        *,
        allowed_local_media_path: str | Path = ".",
        download_dir: str | Path = ".slopperly/runtimes/vllm-omni",
    ):
        self.venv = Path(venv)
        self.url = url
        self.allowed_local_media_path = Path(allowed_local_media_path)
        self.download_dir = Path(download_dir)

    def health(self) -> dict:
        return VllmOmniTtsClient(self.url).health()

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    @property
    def vllm_omni(self) -> Path:
        return self.venv / "bin" / "vllm-omni"

    def launch_command(self, model: str) -> list[str]:
        host, port = local_host_port(self.url, default_port=8091, label="vLLM-Omni")
        return [
            str(self.vllm_omni),
            "serve",
            model,
            "--omni",
            "--host",
            host,
            "--port",
            str(port),
            "--allowed-local-media-path",
            str(self.allowed_local_media_path.resolve()),
            "--download-dir",
            str(self.download_dir.resolve()),
        ]

    def preflight(self) -> list[InstallStep]:
        return [executable_check(self.vllm_omni, name="vllm-omni")]

    def start(self, model: str) -> subprocess.Popen:
        require_preflight(self.preflight())
        return subprocess.Popen(self.launch_command(model))
