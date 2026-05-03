import asyncio
import ssl
from typing import Optional

import aiohttp

from octobot_tunnel.client.exceptions import RetryableError

# HTTP status codes that indicate a transient failure — same set as the Go client
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

_HANDSHAKE_TIMEOUT = 60.0


class WebSocketTransport:
    """
    Wraps an aiohttp WebSocket connection as a byte-stream for yamux.

    yamux reads/writes frames as raw bytes; WebSocket is message-based.
    We buffer incoming binary messages into an asyncio.StreamReader so that
    yamux can call read_exactly(n) as if reading from a TCP stream.
    """

    def __init__(self, ws: aiohttp.ClientWebSocketResponse, session: aiohttp.ClientSession):
        self._ws = ws
        self._aiohttp_session = session
        self._reader: asyncio.StreamReader = asyncio.StreamReader()
        self._read_task: asyncio.Task = asyncio.ensure_future(self._read_loop())

    async def _read_loop(self) -> None:
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    self._reader.feed_data(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception:
            pass
        finally:
            self._reader.feed_eof()

    async def read(self, n: int = -1) -> bytes:
        """Read up to n bytes (like net.Conn.Read), or all until EOF when n=-1."""
        if n == -1:
            return await self._reader.read(-1)
        return await self._reader.read(n)

    async def read_exactly(self, n: int) -> bytes:
        """Read exactly n bytes; used internally by yamux frame parsing."""
        return await self._reader.readexactly(n)

    async def write(self, data: bytes) -> None:
        await self._ws.send_bytes(data)

    async def close(self) -> None:
        if not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await self._ws.close()
        except Exception:
            pass
        try:
            await self._aiohttp_session.close()
        except Exception:
            pass


async def dial_websocket(
    url: str,
    token: Optional[str] = None,
    tenant_id: Optional[str] = None,
    ssl_context: Optional[ssl.SSLContext] = None,
    proxy_url: Optional[str] = None,
) -> WebSocketTransport:
    """
    Establish a WebSocket connection and return a WebSocketTransport.

    Raises RetryableError for transient HTTP failures, or the underlying
    aiohttp exception for permanent failures.
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if tenant_id:
        headers["x-piko-tenant-id"] = tenant_id

    connector = aiohttp.TCPConnector(ssl=ssl_context)
    session = aiohttp.ClientSession(connector=connector)
    try:
        ws = await session.ws_connect(
            url,
            headers=headers,
            proxy=proxy_url,
            timeout=aiohttp.ClientWSTimeout(ws_close=_HANDSHAKE_TIMEOUT),
        )
        return WebSocketTransport(ws, session)
    except aiohttp.WSServerHandshakeError as exc:
        await session.close()
        if exc.status in _RETRYABLE_STATUS_CODES:
            raise RetryableError(str(exc), status_code=exc.status) from exc
        raise
    except Exception:
        await session.close()
        raise
