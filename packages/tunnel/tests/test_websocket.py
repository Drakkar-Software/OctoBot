import asyncio
import ssl
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

import aiohttp

from octobot_tunnel.client.exceptions import RetryableError
from octobot_tunnel.client.websocket import WebSocketTransport, dial_websocket, _RETRYABLE_STATUS_CODES

pytestmark = pytest.mark.asyncio


def make_mock_ws(messages=None):
    """
    Build a mock WebSocket that properly supports `async for msg in ws`.

    Python's special-method lookup goes via the TYPE, not the instance, so we
    cannot patch __aiter__ on an AsyncMock instance.  Use a real class instead.
    """
    if messages is None:
        messages = []
    _messages = list(messages)

    class _AsyncIter:
        def __init__(self):
            self._iter = iter(_messages)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    class MockWS:
        closed = False
        send_bytes = AsyncMock()
        close = AsyncMock()

        def __aiter__(self):
            return _AsyncIter()

    ws = MockWS()
    ws.send_bytes = AsyncMock()
    ws.close = AsyncMock()
    return ws


def make_ws_msg(data: bytes):
    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.BINARY
    msg.data = data
    return msg


def make_close_msg():
    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.CLOSE
    msg.data = None
    return msg


class TestWebSocketTransport:
    async def test_binary_message_feeds_reader(self):
        msgs = [make_ws_msg(b"hello"), make_close_msg()]
        ws = make_mock_ws(msgs)
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await asyncio.sleep(0.05)  # let read loop run
        data = await asyncio.wait_for(transport.read_exactly(5), timeout=1.0)
        assert data == b"hello"
        await transport.close()

    async def test_multiple_messages_buffered(self):
        msgs = [make_ws_msg(b"foo"), make_ws_msg(b"bar"), make_close_msg()]
        ws = make_mock_ws(msgs)
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await asyncio.sleep(0.05)
        data = await asyncio.wait_for(transport.read_exactly(6), timeout=1.0)
        assert data == b"foobar"
        await transport.close()

    async def test_close_message_feeds_eof(self):
        msgs = [make_close_msg()]
        ws = make_mock_ws(msgs)
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await asyncio.sleep(0.05)
        with pytest.raises(asyncio.IncompleteReadError):
            await asyncio.wait_for(transport.read_exactly(10), timeout=1.0)
        await transport.close()

    async def test_read_returns_available_bytes(self):
        msgs = [make_ws_msg(b"hello"), make_close_msg()]
        ws = make_mock_ws(msgs)
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await asyncio.sleep(0.05)
        # read(100) returns whatever is available, not exactly 100 bytes
        data = await asyncio.wait_for(transport.read(100), timeout=1.0)
        assert data == b"hello"
        await transport.close()

    async def test_write_sends_binary_message(self):
        ws = make_mock_ws([make_close_msg()])
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await transport.write(b"data to send")
        ws.send_bytes.assert_awaited_once_with(b"data to send")
        await transport.close()

    async def test_close_closes_ws_and_session(self):
        ws = make_mock_ws([make_close_msg()])
        session = AsyncMock(spec=aiohttp.ClientSession)
        transport = WebSocketTransport(ws, session)
        await transport.close()
        ws.close.assert_awaited_once()
        session.close.assert_awaited_once()


class TestDialWebSocket:
    async def test_connects_with_bearer_token(self):
        mock_transport = MagicMock(spec=WebSocketTransport)
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            mock_ws = make_mock_ws([make_close_msg()])
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)

            transport = await dial_websocket(
                url="ws://localhost:8001/piko/v1/upstream/ep",
                token="mytoken",
            )
            _, kwargs = mock_session.ws_connect.call_args
            headers = kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer mytoken"
            await transport.close()

    async def test_connects_with_tenant_id(self):
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            mock_ws = make_mock_ws([make_close_msg()])
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)

            transport = await dial_websocket(
                url="ws://localhost:8001/piko/v1/upstream/ep",
                tenant_id="tenant-123",
            )
            _, kwargs = mock_session.ws_connect.call_args
            headers = kwargs.get("headers", {})
            assert headers.get("x-piko-tenant-id") == "tenant-123"
            await transport.close()

    async def test_connects_without_auth_has_no_extra_headers(self):
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            mock_ws = make_mock_ws([make_close_msg()])
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)

            transport = await dial_websocket(url="ws://localhost:8001/piko/v1/upstream/ep")
            _, kwargs = mock_session.ws_connect.call_args
            headers = kwargs.get("headers", {})
            assert "Authorization" not in headers
            assert "x-piko-tenant-id" not in headers
            await transport.close()

    @pytest.mark.parametrize("status_code", sorted(_RETRYABLE_STATUS_CODES))
    async def test_retryable_error_on_retryable_status(self, status_code):
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            exc = aiohttp.WSServerHandshakeError(
                request_info=MagicMock(),
                history=(),
                status=status_code,
                message=f"status {status_code}",
            )
            mock_session.ws_connect = AsyncMock(side_effect=exc)

            with pytest.raises(RetryableError) as exc_info:
                await dial_websocket(url="ws://localhost:8001/ep")
            assert exc_info.value.status_code == status_code

    async def test_non_retryable_error_on_other_status(self):
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            exc = aiohttp.WSServerHandshakeError(
                request_info=MagicMock(),
                history=(),
                status=403,
                message="forbidden",
            )
            mock_session.ws_connect = AsyncMock(side_effect=exc)

            with pytest.raises(aiohttp.WSServerHandshakeError):
                await dial_websocket(url="ws://localhost:8001/ep")

    async def test_proxy_url_forwarded_to_aiohttp(self):
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector"):
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            mock_ws = make_mock_ws([make_close_msg()])
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)

            transport = await dial_websocket(
                url="ws://localhost:8001/ep",
                proxy_url="http://proxy:3128",
            )
            _, kwargs = mock_session.ws_connect.call_args
            assert kwargs.get("proxy") == "http://proxy:3128"
            await transport.close()

    async def test_ssl_context_forwarded_to_connector(self):
        ctx = ssl.create_default_context()
        with patch("octobot_tunnel.client.websocket.aiohttp.ClientSession") as MockSession, \
             patch("octobot_tunnel.client.websocket.aiohttp.TCPConnector") as MockConnector:
            mock_session = AsyncMock()
            MockSession.return_value = mock_session
            mock_ws = make_mock_ws([make_close_msg()])
            mock_session.ws_connect = AsyncMock(return_value=mock_ws)

            transport = await dial_websocket(url="wss://localhost:8001/ep", ssl_context=ctx)
            MockConnector.assert_called_once_with(ssl=ctx)
            await transport.close()
