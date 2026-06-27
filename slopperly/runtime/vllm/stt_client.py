"""vLLM OpenAI-compatible speech-to-text client."""

from __future__ import annotations

from ..http_utils import LocalHttpClient, file_part


class VllmSttClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8090", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_url", "http://127.0.0.1:8090"))

    def health(self) -> dict:
        return self.http.get_json("/v1/models")

    def transcribe(
        self,
        audio_path: str,
        *,
        model: str = "openai/whisper-large-v3-turbo",
        language: str | None = None,
        response_format: str = "verbose_json",
    ) -> dict:
        fields = {
            "model": model,
            "response_format": response_format,
        }
        if language:
            fields["language"] = language
        resp = self.http.post_multipart(
            "/v1/audio/transcriptions",
            fields=fields,
            files={"file": file_part(audio_path)},
        )
        if isinstance(resp, dict):
            return resp
        return {"text": str(resp)}
