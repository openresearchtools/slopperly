"""vLLM multimodal chat client for local image/video captioning."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..errors import RuntimeUnavailableError
from ..http_utils import LocalHttpClient

DEFAULT_VLM_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"


class VllmVlmClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8090", *, timeout: float = 300.0):
        self.http = LocalHttpClient(base_url, label="vLLM", timeout=timeout)

    @classmethod
    def from_preferences(cls, prefs):
        return cls(getattr(prefs, "vllm_url", "http://127.0.0.1:8090"))

    def health(self) -> dict:
        return self.http.get_json("/v1/models")

    def chat(self, payload: dict) -> dict:
        return self.http.post_json("/v1/chat/completions", payload)

    def caption_video(
        self,
        video_path: str,
        *,
        model: str = DEFAULT_VLM_MODEL,
        duration_seconds: float,
        clip_start_seconds: float = 0.0,
        max_tokens: int = 768,
        speed: str = "BALANCED",
    ) -> dict:
        prompt = (
            "You are generating dense timeline captions for a Blender video strip. "
            "Watch the attached local video and return only JSON with this schema: "
            '{"scene": string, "events": [{"start": number, "end": number, '
            '"description": string}]}. Times are seconds in the attached file timebase. '
            f"Only report events in seconds {clip_start_seconds:.3f} "
            f"through {clip_start_seconds + duration_seconds:.3f}. Produce concise "
            "events that can become VSE text strips. "
            f"Speed profile: {speed}."
        )
        payload = self._video_chat_payload(
            video_path,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
        )
        response = self.chat(payload)
        content = _choice_content(response)
        return normalize_caption_response(
            content,
            duration_seconds=duration_seconds,
            clip_start_seconds=clip_start_seconds,
        )

    def find_video(
        self,
        video_path: str,
        *,
        query: str,
        model: str = DEFAULT_VLM_MODEL,
        duration_seconds: float,
        clip_start_seconds: float = 0.0,
        max_tokens: int = 128,
    ) -> dict:
        prompt = (
            "You are searching a local video clip for one requested event. "
            "Return only JSON with this schema: "
            '{"format_ok": boolean, "span": [start_seconds, end_seconds] | null, '
            '"description": string}. Times are seconds in the attached file timebase. '
            f"Only report a span within seconds {clip_start_seconds:.3f} "
            f"through {clip_start_seconds + duration_seconds:.3f}. "
            f"Requested event: {query!r}."
        )
        payload = self._video_chat_payload(
            video_path,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
        )
        response = self.chat(payload)
        content = _choice_content(response)
        return normalize_find_response(
            content,
            duration_seconds=duration_seconds,
            clip_start_seconds=clip_start_seconds,
        )

    def _video_chat_payload(
        self,
        video_path: str,
        *,
        model: str,
        prompt: str,
        max_tokens: int,
    ) -> dict:
        uri = Path(video_path).expanduser().resolve().as_uri()
        return {
            "model": model,
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": {"url": uri}},
                    ],
                }
            ],
        }


def _choice_content(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeUnavailableError(f"vLLM VLM response missing chat content: {response}") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def normalize_caption_response(
    raw: str | dict,
    *,
    duration_seconds: float,
    clip_start_seconds: float = 0.0,
) -> dict:
    data = _json_object(raw)
    lower = float(clip_start_seconds)
    upper = lower + float(duration_seconds)
    scene = str(data.get("scene") or data.get("summary") or "").strip()
    events = []
    for raw_event in data.get("events") or data.get("captions") or []:
        if not isinstance(raw_event, dict):
            continue
        start = _as_float(raw_event.get("start", raw_event.get("start_seconds")), default=0.0)
        end = _as_float(raw_event.get("end", raw_event.get("end_seconds")), default=start + 1.0)
        description = str(
            raw_event.get("description")
            or raw_event.get("text")
            or raw_event.get("caption")
            or ""
        ).strip()
        start = max(lower, min(upper, start))
        if start >= upper:
            continue
        end = max(start + 0.01, min(upper, end))
        if description:
            events.append({"start": start, "end": end, "description": description})
    if not events and scene:
        events.append({"start": lower, "end": max(lower + 1.0, upper), "description": scene})
    return {"scene": scene, "events": events}


def normalize_find_response(
    raw: str | dict,
    *,
    duration_seconds: float,
    clip_start_seconds: float = 0.0,
) -> dict:
    data = _json_object(raw)
    lower = float(clip_start_seconds)
    upper = lower + float(duration_seconds)
    span = data.get("span")
    if isinstance(span, dict):
        span = [span.get("start"), span.get("end")]
    format_ok = bool(data.get("format_ok", span is not None))
    if not isinstance(span, (list, tuple)) or len(span) < 2:
        return {"format_ok": False, "span": None, "description": str(data.get("description") or "")}
    start = _as_float(span[0], default=0.0)
    end = _as_float(span[1], default=start + 1.0)
    start = max(lower, min(upper, start))
    if start >= upper:
        return {
            "format_ok": False,
            "span": None,
            "description": str(data.get("description") or ""),
        }
    end = max(start + 0.01, min(upper, end))
    return {
        "format_ok": format_ok,
        "span": [start, end],
        "description": str(data.get("description") or ""),
    }


def _json_object(raw: str | dict) -> dict:
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise RuntimeUnavailableError(f"vLLM VLM response was not JSON: {text[:300]}") from exc
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise RuntimeUnavailableError(f"vLLM VLM response JSON must be an object: {parsed!r}")
    return parsed


def _as_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
