import asyncio
import ssl
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from octobot_tunnel.client.exceptions import RetryableError
from octobot_tunnel.client.upstream import Upstream, _DEFAULT_UPSTREAM_URL
from octobot_tunnel.client.listener import Listener
from octobot_tunnel.client.forwarder import Forwarder

pytestmark = pytest.mark.asyncio


def make_mock_session():
    session = AsyncMock()
    session._closed = False
    session.accept = AsyncMock(side_effect=asyncio.CancelledError)
    session.close = AsyncMock()
    session.start = MagicMock()
    return session


class TestUpstreamURL:
    def test_listen_url_http_to_ws(self):
        up = Upstream(url="http://myhost:8001")
        assert up._listen_url("ep") == "ws://myhost:8001/piko/v1/upstream/ep"

    def test_listen_url_https_to_wss(self):
        up = Upstream(url="https://myhost:8001")
        assert up._listen_url("ep") == "wss://myhost:8001/piko/v1/upstream/ep"

    def test_listen_url_default(self):
        up = Upstream()
        assert up._listen_url("my-ep") == "ws://localhost:8001/piko/v1/upstream/my-ep"

    def test_listen_url_with_existing_path(self):
        up = Upstream(url="http://host:8001/prefix")
        url = up._listen_url("ep")
        assert url == "ws://host:8001/prefix/piko/v1/upstream/ep"

    def test_listen_url_with_trailing_slash(self):
        up = Upstream(url="http://host:8001/")
        url = up._listen_url("ep")
        assert "/piko/v1/upstream/ep" in url
        assert "//" not in url.split("://", 1)[1]


class TestUpstreamConnect:
    async def test_listen_returns_listener(self):
        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="http://localhost:8001")
            ln = await up.listen("my-ep")
            assert isinstance(ln, Listener)
            assert ln.endpoint_id() == "my-ep"

    async def test_listen_and_forward_returns_forwarder(self):
        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="http://localhost:8001")
            fwd = await up.listen_and_forward("my-ep", "localhost:9000")
            assert isinstance(fwd, Forwarder)
            await fwd.close()

    async def test_connect_retries_on_retryable_error(self):
        call_count = 0

        async def dial_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("transient", status_code=503)
            return MagicMock()

        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", side_effect=dial_side_effect), \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession, \
             patch("octobot_tunnel.client.upstream.asyncio.sleep", new_callable=AsyncMock):
            MockSession.return_value = mock_session
            up = Upstream(url="http://localhost:8001", min_reconnect_backoff=0.001, max_reconnect_backoff=0.01)
            await up._connect("ep")
            assert call_count == 3

    async def test_connect_aborts_on_non_retryable_error(self):
        async def dial_side_effect(*args, **kwargs):
            raise ValueError("permanent error")

        with patch("octobot_tunnel.client.upstream.dial_websocket", side_effect=dial_side_effect):
            up = Upstream(url="http://localhost:8001")
            with pytest.raises(ValueError, match="permanent error"):
                await up._connect("ep")

    async def test_connect_passes_token_to_dial(self):
        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="http://localhost:8001", token="secret")
            await up._connect("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("token") == "secret"

    async def test_connect_passes_tenant_id_to_dial(self):
        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="http://localhost:8001", tenant_id="tenant-42")
            await up._connect("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("tenant_id") == "tenant-42"

    async def test_connect_passes_proxy_url_to_dial(self):
        mock_session = make_mock_session()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="http://localhost:8001", proxy_url="http://proxy:3128")
            await up._connect("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("proxy_url") == "http://proxy:3128"

    async def test_connect_passes_tls_context_to_dial(self):
        mock_session = make_mock_session()
        ctx = ssl.create_default_context()
        with patch("octobot_tunnel.client.upstream.dial_websocket", new_callable=AsyncMock) as mock_dial, \
             patch("octobot_tunnel.client.upstream.YamuxSession") as MockSession:
            mock_dial.return_value = MagicMock()
            MockSession.return_value = mock_session

            up = Upstream(url="https://localhost:8001", tls_context=ctx)
            await up._connect("ep")
            _, kwargs = mock_dial.call_args
            assert kwargs.get("ssl_context") is ctx
