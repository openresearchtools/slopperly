"""Minimal ComfyUI HTTP API client for local-only workflow execution."""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..errors import RuntimeUnavailableError
from ..local_url import assert_local_http_url


class ComfyApiClient:
    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = assert_local_http_url(base_url, label="ComfyUI").rstrip("/")
        self.timeout = timeout

    def _url(self, path: str, query: dict | None = None) -> str:
        url = self.base_url + "/" + path.lstrip("/")
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return url

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict | None = None,
        expect_json: bool = True,
        timeout: float | None = None,
        query: dict | None = None,
    ):
        req = urllib.request.Request(
            self._url(path, query),
            data=data,
            method=method,
            headers=headers or {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                body = resp.read()
                if not expect_json:
                    return body, resp.headers
                return json.loads(body.decode("utf-8")) if body else {}
        except urllib.error.URLError as exc:
            raise RuntimeUnavailableError(f"ComfyUI {method} {path} failed: {exc}") from exc

    def object_info(self) -> dict:
        return self._request("GET", "/object_info")

    def queue_prompt(self, workflow: dict) -> str:
        body = json.dumps({"prompt": workflow}).encode("utf-8")
        resp = self._request(
            "POST",
            "/prompt",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        prompt_id = resp.get("prompt_id")
        if not prompt_id:
            raise RuntimeUnavailableError(f"ComfyUI /prompt returned no prompt_id: {resp}")
        return prompt_id

    def history(self, prompt_id: str) -> dict:
        return self._request("GET", f"/history/{prompt_id}")

    def wait_for_history(self, prompt_id: str, *, timeout: float, poll: float = 1.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            hist = self.history(prompt_id)
            if prompt_id in hist:
                return hist[prompt_id]
            time.sleep(poll)
        raise RuntimeUnavailableError(f"ComfyUI prompt {prompt_id} timed out after {timeout:.0f}s")

    def view(self, filename: str, subfolder: str = "", file_type: str = "output") -> bytes:
        body, _ = self._request(
            "GET",
            "/view",
            query={"filename": filename, "subfolder": subfolder, "type": file_type},
            expect_json=False,
        )
        return body

    def upload_file(self, path: str, *, image_type: str = "input") -> dict:
        file_path = Path(path)
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        boundary = "----SlopperlyComfyBoundary"
        payload = []
        payload.append(f"--{boundary}\r\n".encode())
        payload.append(
            f'Content-Disposition: form-data; name="image"; filename="{file_path.name}"\r\n'.encode()
        )
        payload.append(f"Content-Type: {mime}\r\n\r\n".encode())
        payload.append(file_path.read_bytes())
        payload.append(b"\r\n")
        payload.append(f"--{boundary}\r\n".encode())
        payload.append(b'Content-Disposition: form-data; name="type"\r\n\r\n')
        payload.append(image_type.encode())
        payload.append(b"\r\n")
        payload.append(f"--{boundary}--\r\n".encode())
        return self._request(
            "POST",
            "/upload/image",
            data=b"".join(payload),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
