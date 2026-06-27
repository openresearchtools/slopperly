"""vLLM process helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from slopperly.runtime.install_utils import InstallStep
from slopperly.runtime.supervisor_utils import (
    executable_check,
    local_host_port,
    require_preflight,
)

from .stt_client import VllmSttClient


class VllmSupervisor:
    def __init__(
        self,
        venv: str | Path = ".slopperly/vllm-venv",
        url: str = "http://127.0.0.1:8090",
        *,
        allowed_local_media_path: str | Path = ".",
    ):
        self.venv = Path(venv)
        self.url = url
        self.allowed_local_media_path = Path(allowed_local_media_path)

    def health(self) -> dict:
        return VllmSttClient(self.url).health()

    @property
    def python(self) -> Path:
        return self.venv / "bin" / "python"

    def launch_command(
        self,
        model: str = "openai/whisper-large-v3-turbo",
        *,
        served_model_name: str | None = None,
        download_dir: str | Path | None = None,
        max_model_len: int | None = None,
        gpu_memory_utilization: float | None = None,
        cpu_offload_gb: float | None = None,
        max_num_seqs: int | None = None,
        limit_mm_per_prompt: dict[str, Any] | None = None,
        media_io_kwargs: dict[str, Any] | None = None,
        mm_processor_cache_gb: float | None = None,
        enforce_eager: bool = False,
    ) -> list[str]:
        host, port = local_host_port(self.url, default_port=8090, label="vLLM")
        command = [
            str(self.python),
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--host",
            host,
            "--port",
            str(port),
            "--model",
            model,
            "--allowed-local-media-path",
            str(self.allowed_local_media_path.resolve()),
        ]
        if served_model_name:
            command.extend(["--served-model-name", served_model_name])
        if download_dir:
            command.extend(["--download-dir", str(Path(download_dir).resolve())])
        if max_model_len is not None:
            command.extend(["--max-model-len", str(int(max_model_len))])
        if gpu_memory_utilization is not None:
            command.extend(["--gpu-memory-utilization", str(float(gpu_memory_utilization))])
        if cpu_offload_gb is not None:
            command.extend(["--cpu-offload-gb", str(float(cpu_offload_gb))])
        if max_num_seqs is not None:
            command.extend(["--max-num-seqs", str(int(max_num_seqs))])
        if limit_mm_per_prompt:
            command.extend(["--limit-mm-per-prompt", json.dumps(limit_mm_per_prompt)])
        if media_io_kwargs:
            command.extend(["--media-io-kwargs", json.dumps(media_io_kwargs)])
        if mm_processor_cache_gb is not None:
            command.extend(["--mm-processor-cache-gb", str(float(mm_processor_cache_gb))])
        if enforce_eager:
            command.append("--enforce-eager")
        return command

    def preflight(self) -> list[InstallStep]:
        return [executable_check(self.python, name="python")]

    def start(self, model: str = "openai/whisper-large-v3-turbo", **kwargs) -> subprocess.Popen:
        require_preflight(self.preflight())
        return subprocess.Popen(self.launch_command(model, **kwargs))
