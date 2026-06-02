import ssl
from typing import Optional
from urllib.parse import urlparse, urlunparse

from octobot_tunnel.client.websocket import dial_websocket, WebSocketTransport

_DEFAULT_PROXY_URL = "http://localhost:8000"


class Stream:
    """
    A connection to a Piko endpoint, equivalent to net.Conn in the Go client.

    For the Dialer side (TCP proxy port) this is a thin wrapper around the
    WebSocket transport — no yamux multiplexing is needed because each Dial()
    call gets its own WebSocket connection.
    """

    def __init__(self, transport: WebSocketTransport):
        self._transport = transport

    async def read(self, n: int = -1) -> bytes:
        return await self._transport.read(n)

    async def write(self, data: bytes) -> None:
        await self._transport.write(data)

    async def close(self) -> None:
        await self._transport.close()


class Dialer:
    """
    Opens TCP connections to Piko endpoints via the proxy port (default 8000).

    Equivalent to the Go client's Dialer struct.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        tls_context: Optional[ssl.SSLContext] = None,
    ):
        self.url = url
        self.token = token
        self.tls_context = tls_context

    async def dial(self, endpoint_id: str) -> Stream:
        """Open a TCP connection to the given endpoint and return a Stream."""
        transport = await dial_websocket(
            url=self._dial_url(endpoint_id),
            token=self.token,
            ssl_context=self.tls_context,
        )
        return Stream(transport)

    def _dial_url(self, endpoint_id: str) -> str:
        base = self.url or _DEFAULT_PROXY_URL
        parsed = urlparse(base)
        scheme = {"http": "ws", "https": "wss"}.get(parsed.scheme, parsed.scheme)
        path = (parsed.path or "").rstrip("/") + f"/_piko/v1/tcp/{endpoint_id}"
        return urlunparse((scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
