"""vLLM OpenAI-compatible speech-to-text client."""

from __future__ import annotations

from ..errors import RuntimeUnavailableError
from ..http_utils import LocalHttpClient, file_part

DEFAULT_STT_MODEL = "openai/whisper-large-v3-turbo"


class VllmSttClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8090", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_url", "http://127.0.0.1:8090"))

    def health(self) -> dict:
        return self.http.get_json("/v1/models")

    def served_model_id(self, requested_model: str) -> str:
        """Use vLLM's single advertised local-path ID for the default STT model."""
        try:
            models = self.health().get("data", [])
        except RuntimeUnavailableError:
            return requested_model
        served_ids = [str(item.get("id")) for item in models if item.get("id")]
        if requested_model in served_ids:
            return requested_model
        if requested_model == DEFAULT_STT_MODEL and len(served_ids) == 1:
            return served_ids[0]
        return requested_model

    def transcribe(
        self,
        audio_path: str,
        *,
        model: str = DEFAULT_STT_MODEL,
        language: str | None = None,
        response_format: str = "verbose_json",
    ) -> dict:
        fields = {
            "model": self.served_model_id(model),
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
