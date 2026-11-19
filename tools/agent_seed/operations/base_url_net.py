#  Host/port parsing and TCP reachability for agent-seed base URLs.

import socket
import urllib.parse

_DEFAULT_CONNECT_TIMEOUT_SECONDS = 2.0


def parse_host_port(base_url: str) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return host, port


def is_tcp_port_accepting(
    host: str,
    port: int,
    connect_timeout_seconds: float = _DEFAULT_CONNECT_TIMEOUT_SECONDS,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=connect_timeout_seconds):
            return True
    except OSError:
        return False
