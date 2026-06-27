"""vLLM-Omni OpenAI-compatible speech client."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..errors import RuntimeUnavailableError
from ..http_utils import LocalHttpClient, write_audio_response


def _local_audio_data_uri(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeUnavailableError(f"reference audio file does not exist: {resolved}")
    mime_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _speech_ref_audio_value(ref_audio: str | None) -> str | None:
    if not ref_audio:
        return None
    value = str(ref_audio).strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "data"}:
        return value
    if parsed.scheme == "file":
        return _local_audio_data_uri(Path(unquote(parsed.path)))
    return _local_audio_data_uri(Path(value))


class VllmOmniTtsClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8091", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM-Omni", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_omni_url", "http://127.0.0.1:8091"))

    def health(self) -> dict:
        return self.http.get_json("/v1/models")

    def speech(
        self,
        *,
        text: str,
        output_path: str,
        model: str,
        voice: str | None = None,
        ref_audio: str | None = None,
        ref_text: str | None = None,
        speed: float | None = None,
        instructions: str | None = None,
        language: str | None = None,
        seed: int | None = None,
        extra_params: dict | None = None,
        response_format: str = "wav",
    ) -> str:
        payload = {
            "model": model,
            "input": text,
            "response_format": response_format,
        }
        if voice:
            payload["voice"] = voice
        ref_audio_value = _speech_ref_audio_value(ref_audio)
        if ref_audio_value:
            payload["ref_audio"] = ref_audio_value
        if ref_text:
            payload["ref_text"] = ref_text
        if speed is not None:
            payload["speed"] = speed
        if instructions:
            payload["instructions"] = instructions
        if language:
            payload["language"] = language
        if seed is not None:
            payload["seed"] = seed
        if extra_params:
            payload["extra_params"] = extra_params

        body = self.http.post_json("/v1/audio/speech", payload, expect_json=False)
        return write_audio_response(body, output_path, client=self.http)
