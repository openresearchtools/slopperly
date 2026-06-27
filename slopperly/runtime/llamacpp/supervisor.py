"""llama.cpp process helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.supervisor_utils import (
    executable_check,
    file_check,
    local_host_port,
    require_preflight,
)

from .client import LlamaCppClient
from .install import find_server_binary


class LlamaCppSupervisor:
    def __init__(self, runtime_root: str | Path, url: str = "http://127.0.0.1:8092"):
        self.runtime_root = Path(runtime_root)
        self.url = url

    @property
    def llama_root(self) -> Path:
        return self.runtime_root / "llama.cpp"

    @property
    def binary(self) -> Path:
        return find_server_binary(self.llama_root) or self.llama_root / "llama-server"

    def health(self) -> dict:
        return LlamaCppClient(self.url).health()

    def launch_command(
        self,
        model_path: str,
        *,
        context_length: int = 60000,
        max_new_tokens: int = 30000,
    ) -> list[str]:
        host, port = local_host_port(self.url, default_port=8092, label="llama.cpp")
        return [
            str(self.binary),
            "--host",
            host,
            "--port",
            str(port),
            "--model",
            model_path,
            "--ctx-size",
            str(context_length),
            "--n-predict",
            str(max_new_tokens),
        ]

    def preflight(self, model_path: str) -> list[InstallStep]:
        return [
            executable_check(self.binary, name="llama-server"),
            file_check(Path(model_path), name="model"),
        ]

    def start(self, model_path: str) -> subprocess.Popen:
        require_preflight(self.preflight(model_path))
        cmd = self.launch_command(model_path)
        return subprocess.Popen(cmd, cwd=str(self.llama_root))
