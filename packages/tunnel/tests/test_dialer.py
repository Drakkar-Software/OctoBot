import asyncio
import ssl
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from octobot_tunnel.client.dialer import Dialer, Stream

pytestmark = pytest.mark.asyncio


class TestDialerURL:
    def test_dial_url_http_to_ws(self):
        d = Dialer(url="http://myhost:8000")
        assert d._dial_url("ep") == "ws://myhost:8000/_piko/v1/tcp/ep"

    def test_dial_url_https_to_wss(self):
        d = Dialer(url="https://myhost:8000")
        assert d._dial_url("ep") == "wss://myhost:8000/_piko/v1/tcp/ep"

    def test_dial_url_default(self):
        d = Dialer()
        assert d._dial_url("my-ep") == "ws://localhost:8000/_piko/v1/tcp/my-ep"

    def test_dial_url_with_existing_path(self):
        d = Dialer(url="http://host:8000/prefix")
        url = d._dial_url("ep")
        assert url == "ws://host:8000/prefix/_piko/v1/tcp/ep"

    def test_dial_url_with_trailing_slash(self):
        d = Dialer(url="http://host:8000/")
        url = d._dial_url("ep")
        assert "/_piko/v1/tcp/ep" in url


class TestDialerDial:
    async def test_dial_returns_stream(self):
        mock_transport = MagicMock()
        mock_transport._reader = MagicMock()
        with patch("octobot_tunnel.client.dialer.dial_websocket", new_callable=AsyncMock) as mock_dial:
            mock_dial.return_value = mock_transport
            d = Dialer(url="http://localhost:8000")
            stream = await d.dial("my-ep")
            assert isinstance(stream, Stream)

    async def test_dial_passes_token(self):
        mock_transport = MagicMock()
        mock_transport._reader = MagicMock()
        with patch("octobot_tunnel.client.dialer.dial_websocket", new_callable=AsyncMock) as mock_dial:
            mock_dial.return_value = mock_transport
            d = Dialer(url="http://localhost:8000", token="mytoken")
            await d.dial("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("token") == "mytoken"

    async def test_dial_passes_tls_context(self):
        ctx = ssl.create_default_context()
        mock_transport = MagicMock()
        mock_transport._reader = MagicMock()
        with patch("octobot_tunnel.client.dialer.dial_websocket", new_callable=AsyncMock) as mock_dial:
            mock_dial.return_value = mock_transport
            d = Dialer(url="https://localhost:8000", tls_context=ctx)
            await d.dial("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("ssl_context") is ctx

    async def test_dial_raises_on_connection_error(self):
        with patch("octobot_tunnel.client.dialer.dial_websocket", new_callable=AsyncMock) as mock_dial:
            mock_dial.side_effect = ConnectionRefusedError("refused")
            d = Dialer(url="http://localhost:8000")
            with pytest.raises(ConnectionRefusedError):
                await d.dial("ep")

    async def test_dial_uses_correct_url(self):
        mock_transport = MagicMock()
        mock_transport._reader = MagicMock()
        with patch("octobot_tunnel.client.dialer.dial_websocket", new_callable=AsyncMock) as mock_dial:
            mock_dial.return_value = mock_transport
            d = Dialer(url="http://piko.example.com:8000")
            await d.dial("endpoint-xyz")
            called_url = mock_dial.call_args[1].get("url") or mock_dial.call_args[0][0]
            assert "endpoint-xyz" in called_url
            assert "_piko/v1/tcp" in called_url


class TestStream:
    async def test_read_delegates_to_transport(self):
        transport = MagicMock()
        transport.read = AsyncMock(return_value=b"hello")
        stream = Stream(transport)
        data = await stream.read(5)
        assert data == b"hello"
        transport.read.assert_awaited_once_with(5)

    async def test_read_minus_one_reads_until_eof(self):
        transport = MagicMock()
        transport.read = AsyncMock(return_value=b"all data")
        stream = Stream(transport)
        data = await stream.read(-1)
        assert data == b"all data"
        transport.read.assert_awaited_once_with(-1)

    async def test_write_delegates_to_transport(self):
        transport = MagicMock()
        transport.write = AsyncMock()
        stream = Stream(transport)
        await stream.write(b"world")
        transport.write.assert_awaited_once_with(b"world")

    async def test_close_delegates_to_transport(self):
        transport = MagicMock()
        transport.close = AsyncMock()
        stream = Stream(transport)
        await stream.close()
        transport.close.assert_awaited_once()
