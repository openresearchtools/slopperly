"""vLLM-Omni OpenAI-compatible speech client."""

from __future__ import annotations

from ..http_utils import LocalHttpClient, write_audio_response


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
        voice: str = "default",
        ref_audio: str | None = None,
        ref_text: str | None = None,
        speed: float | None = None,
        instructions: str | None = None,
        response_format: str = "wav",
    ) -> str:
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
        }
        if ref_audio:
            payload["ref_audio"] = ref_audio
        if ref_text:
            payload["ref_text"] = ref_text
        if speed is not None:
            payload["speed"] = speed
        if instructions:
            payload["instructions"] = instructions

        body = self.http.post_json("/v1/audio/speech", payload, expect_json=False)
        return write_audio_response(body, output_path, client=self.http)
