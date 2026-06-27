"""Owned ComfyUI runtime health and launch helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.supervisor_utils import (
    dir_check,
    executable_check,
    file_check,
    local_host_port,
    require_preflight,
)

from .api_client import ComfyApiClient


class ComfySupervisor:
    def __init__(self, runtime_root: str | Path, url: str = "http://127.0.0.1:8188"):
        self.runtime_root = Path(runtime_root)
        self.url = url

    @property
    def comfy_root(self) -> Path:
        return self.runtime_root / "ComfyUI"

    @property
    def python(self) -> Path:
        return self.runtime_root / "comfy-venv" / "bin" / "python"

    def health(self) -> dict:
        client = ComfyApiClient(self.url)
        return {"object_info_count": len(client.object_info())}

    def launch_command(self) -> list[str]:
        host, port = local_host_port(self.url, default_port=8188, label="ComfyUI")
        return [
            str(self.python),
            "main.py",
            "--listen",
            host,
            "--port",
            str(port),
        ]

    def preflight(self) -> list[InstallStep]:
        return [
            dir_check(self.comfy_root, name="comfy_root"),
            executable_check(self.python, name="python"),
            file_check(self.comfy_root / "main.py", name="main.py"),
        ]

    def start(self) -> subprocess.Popen:
        require_preflight(self.preflight())
        cmd = self.launch_command()
        return subprocess.Popen(cmd, cwd=str(self.comfy_root))
