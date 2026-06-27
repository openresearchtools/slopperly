"""OpenAI-compatible llama.cpp client for prompt/chat work."""

from __future__ import annotations

from ..errors import RuntimeUnavailableError
from ..http_utils import LocalHttpClient

DEFAULT_CONTEXT_LENGTH = 60000
DEFAULT_MAX_NEW_TOKENS = 30000


class LlamaCppClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8092", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="llama.cpp", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "llamacpp_url", "http://127.0.0.1:8092"))

    def health(self) -> dict:
        try:
            return self.http.get_json("/health")
        except RuntimeUnavailableError:
            return self.http.get_json("/v1/models")

    def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        context_length: int = DEFAULT_CONTEXT_LENGTH,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    ) -> tuple[str, dict]:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_new_tokens,
            "n_predict": max_new_tokens,
            "n_ctx": context_length,
            "stream": False,
        }
        if model:
            payload["model"] = model
        resp = self.http.post_json("/v1/chat/completions", payload)
        text = self._extract_text(resp)
        diagnostics = {
            "requested_context_length": context_length,
            "requested_max_new_tokens": max_new_tokens,
            "usage": resp.get("usage") if isinstance(resp, dict) else None,
        }
        return text, diagnostics

    @staticmethod
    def _extract_text(resp: dict) -> str:
        try:
            choices = resp.get("choices") or []
            if choices:
                msg = choices[0].get("message") or {}
                text = msg.get("content") or choices[0].get("text") or ""
                if text.strip():
                    return text.strip()
        except Exception as exc:
            raise RuntimeUnavailableError(f"llama.cpp response parse failed: {exc}") from exc
        raise RuntimeUnavailableError(f"llama.cpp returned no text: {resp}")
