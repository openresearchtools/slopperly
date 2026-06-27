"""Small stdlib HTTP helpers for local runtime clients."""

from __future__ import annotations

import base64
import json
import mimetypes
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .errors import RuntimeUnavailableError
from .local_url import assert_local_http_url


class LocalHttpClient:
    """HTTP helper that refuses non-local runtime URLs."""

    def __init__(self, base_url: str, *, label: str, timeout: float = 300.0):
        self.base_url = assert_local_http_url(base_url, label=label)
        self.label = label
        self.timeout = timeout

    def url(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict | None = None,
        expect_json: bool = True,
        timeout: float | None = None,
    ):
        req = urllib.request.Request(
            self.url(path),
            data=data,
            method=method,
            headers=headers or {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                if not expect_json:
                    return body, content_type
                if not body:
                    return {}
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeUnavailableError(
                f"{self.label} {method} {path} -> HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeUnavailableError(
                f"{self.label} {method} {path} failed: {exc.reason}"
            ) from exc

    def get_json(self, path: str):
        return self.request("GET", path)

    def post_json(self, path: str, payload: dict, *, expect_json: bool = True):
        return self.request(
            "POST",
            path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            expect_json=expect_json,
        )

    def post_multipart(self, path: str, *, fields: dict, files: dict):
        body, content_type = encode_multipart(fields=fields, files=files)
        return self.request(
            "POST",
            path,
            data=body,
            headers={"Content-Type": content_type, "Accept": "application/json"},
        )


def encode_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = "----SlopperlyBoundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.extend([
            b"--" + boundary.encode("ascii"),
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
            b"",
            str(value).encode("utf-8"),
        ])
    for name, item in files.items():
        filename, data, mime = item
        chunks.extend([
            b"--" + boundary.encode("ascii"),
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"'
            ).encode("utf-8"),
            f"Content-Type: {mime}".encode("utf-8"),
            b"",
            data,
        ])
    chunks.append(b"--" + boundary.encode("ascii") + b"--")
    chunks.append(b"")
    return crlf.join(chunks), f"multipart/form-data; boundary={boundary}"


def file_part(path: str) -> tuple[str, bytes, str]:
    file_path = Path(path)
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return file_path.name, file_path.read_bytes(), mime


def write_audio_response(response, destination: str, *, client: LocalHttpClient) -> str:
    """Persist binary or JSON OpenAI-style audio responses to destination."""
    dst = Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(response, tuple):
        body, content_type = response
        if "json" in (content_type or "").lower():
            response = json.loads(body.decode("utf-8"))
        else:
            dst.write_bytes(body)
            return str(dst)

    if not isinstance(response, dict):
        raise RuntimeUnavailableError(f"Unrecognized audio response: {type(response).__name__}")

    if response.get("b64_json"):
        dst.write_bytes(base64.b64decode(response["b64_json"]))
        return str(dst)
    data = response.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if first.get("b64_json"):
            dst.write_bytes(base64.b64decode(first["b64_json"]))
            return str(dst)
        if first.get("url"):
            return download_local_url(first["url"], dst, client=client)
    if response.get("url"):
        return download_local_url(response["url"], dst, client=client)
    if response.get("audio"):
        dst.write_bytes(base64.b64decode(response["audio"]))
        return str(dst)
    raise RuntimeUnavailableError(f"Speech response did not contain audio: {response}")


def download_local_url(url: str, destination: Path, *, client: LocalHttpClient) -> str:
    assert_local_http_url(url, label=client.label)
    if url.startswith(client.base_url):
        path = url[len(client.base_url):] or "/"
        body, _ = client.request("GET", path, expect_json=False)
    else:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=client.timeout) as resp:
            body = resp.read()
    destination.write_bytes(body)
    return str(destination)
