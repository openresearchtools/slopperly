"""Voice upload helper for vLLM-Omni servers that expose /v1/audio/voices."""

from __future__ import annotations

from ..http_utils import LocalHttpClient, file_part


class VllmOmniVoiceClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8091", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM-Omni", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_omni_url", "http://127.0.0.1:8091"))

    def upload_voice(self, audio_path: str, *, ref_text: str = "", name: str = "") -> dict:
        return self.http.post_multipart(
            "/v1/audio/voices",
            fields={"ref_text": ref_text, "name": name},
            files={"file": file_part(audio_path)},
        )
