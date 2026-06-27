"""vLLM multimodal chat client for local image/video captioning."""

from __future__ import annotations

from ..http_utils import LocalHttpClient


class VllmVlmClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8090", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_url", "http://127.0.0.1:8090"))

    def chat(self, payload: dict) -> dict:
        return self.http.post_json("/v1/chat/completions", payload)
