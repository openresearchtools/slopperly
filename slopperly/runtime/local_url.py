"""URL validation helpers for local-only runtime clients."""

from urllib.parse import urlparse

from .errors import RuntimeUnavailableError

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def assert_local_http_url(url: str, *, label: str = "runtime") -> str:
    """Return a normalized local URL or raise if it points outside this host."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeUnavailableError(f"{label} URL must be http(s): {url!r}")
    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        raise RuntimeUnavailableError(
            f"{label} must be local-only; refusing non-local URL {url!r}."
        )
    return url.rstrip("/")
