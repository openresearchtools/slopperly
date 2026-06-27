"""Runtime network guard for local-only generation tests."""

from __future__ import annotations

import contextlib
import errno
import socket
from collections.abc import Iterator


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class NetworkGuardError(OSError):
    """Raised when a generation test tries to reach a non-local host."""


def _host_from_address(address) -> str | None:
    if isinstance(address, tuple) and address:
        host = address[0]
        if isinstance(host, bytes):
            return host.decode("ascii", "ignore")
        return str(host)
    return None


def _is_allowed_host(host: str | None, allowed_hosts: set[str]) -> bool:
    if host is None:
        return True
    normalized = host.strip("[]").lower()
    return normalized in LOCAL_HOSTS or normalized in allowed_hosts


def _blocked(host: str | None) -> NetworkGuardError:
    return NetworkGuardError(errno.EPERM, f"Slopperly generation may only connect to local runtimes; blocked {host!r}")


@contextlib.contextmanager
def local_only_network(allowed_hosts: set[str] | None = None) -> Iterator[None]:
    """Temporarily block outbound socket connections to non-local hosts.

    Use this around generation tests after model artifacts are already present.
    Unix-domain sockets and localhost/loopback HTTP runtimes remain available.
    """
    allowed = {host.strip("[]").lower() for host in (allowed_hosts or set())}
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def guarded_connect(sock, address):
        host = _host_from_address(address)
        if not _is_allowed_host(host, allowed):
            raise _blocked(host)
        return original_connect(sock, address)

    def guarded_connect_ex(sock, address):
        host = _host_from_address(address)
        if not _is_allowed_host(host, allowed):
            return errno.EPERM
        return original_connect_ex(sock, address)

    def guarded_create_connection(address, timeout=None, source_address=None, *args, **kwargs):
        host = _host_from_address(address)
        if not _is_allowed_host(host, allowed):
            raise _blocked(host)
        return original_create_connection(address, timeout, source_address, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create_connection
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create_connection
