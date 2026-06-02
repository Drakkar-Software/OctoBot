import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from octobot_tunnel.client.exceptions import ConnectionClosed
from octobot_tunnel.client.listener import Listener, PikoAddr
from octobot_tunnel.yamux.stream import YamuxStream

pytestmark = pytest.mark.asyncio


def make_mock_session(streams=None):
    session = MagicMock()
    session._closed = False
    q = asyncio.Queue()
    if streams:
        for s in streams:
            q.put_nowait(s)

    async def accept():
        return await q.get()

    session.accept = accept
    session.close = AsyncMock()
    session._send_frame = AsyncMock()
    return session, q


def make_mock_upstream(session=None):
    upstream = MagicMock()
    upstream._logger = MagicMock(return_value=MagicMock())
    if session is not None:
        upstream._connect = AsyncMock(return_value=session)
    return upstream


def make_mock_stream(stream_id=1):
    stream = MagicMock(spec=YamuxStream)
    stream.stream_id = stream_id
    stream.read = AsyncMock(return_value=b"")
    stream.write = AsyncMock()
    stream.close = AsyncMock()
    return stream


class TestListenerAccept:
    async def test_accept_returns_stream_from_session(self):
        stream = make_mock_stream()
        session, q = make_mock_session(streams=[stream])
        upstream = make_mock_upstream()
        ln = Listener("my-ep", upstream)
        ln._attach_session(session)

        result = await asyncio.wait_for(ln.accept(), timeout=1.0)
        assert result is stream

    async def test_accept_blocks_until_stream_available(self):
        session, q = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        stream = make_mock_stream()

        async def delayed_enqueue():
            await asyncio.sleep(0.05)
            q.put_nowait(stream)

        asyncio.ensure_future(delayed_enqueue())
        result = await asyncio.wait_for(ln.accept(), timeout=1.0)
        assert result is stream

    async def test_accept_with_context_stops_when_event_set(self):
        session, q = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        stop = asyncio.Event()

        async def stopper():
            await asyncio.sleep(0.05)
            stop.set()

        asyncio.ensure_future(stopper())
        with pytest.raises(ConnectionClosed):
            await asyncio.wait_for(ln.accept_with_context(stop), timeout=1.0)

    async def test_accept_raises_connection_closed_after_close(self):
        session, q = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        await ln.close()
        with pytest.raises(ConnectionClosed):
            await ln.accept()

    async def test_accept_reconnects_on_session_error(self):
        # First session raises; second session delivers a stream
        stream = make_mock_stream()
        new_session, new_q = make_mock_session(streams=[stream])
        upstream = make_mock_upstream(session=new_session)

        first_session = MagicMock()
        first_session._closed = False

        accept_count = 0

        async def failing_accept():
            nonlocal accept_count
            accept_count += 1
            raise ConnectionError("session died")

        first_session.accept = failing_accept
        first_session._send_frame = AsyncMock()

        ln = Listener("ep", upstream)
        ln._attach_session(first_session)

        result = await asyncio.wait_for(ln.accept(), timeout=2.0)
        assert result is stream
        upstream._connect.assert_awaited_once_with("ep")


class TestListenerAddr:
    def test_addr_network_is_tcp(self):
        upstream = make_mock_upstream()
        ln = Listener("my-ep", upstream)
        assert ln.addr().network == "tcp"

    def test_addr_string_is_endpoint_id(self):
        upstream = make_mock_upstream()
        ln = Listener("my-ep", upstream)
        assert ln.addr().address == "my-ep"
        assert str(ln.addr()) == "my-ep"

    def test_endpoint_id(self):
        upstream = make_mock_upstream()
        ln = Listener("hello-world", upstream)
        assert ln.endpoint_id() == "hello-world"


class TestPikoAddr:
    def test_default_network(self):
        addr = PikoAddr()
        assert addr.network == "tcp"

    def test_str_returns_address(self):
        addr = PikoAddr(address="test-endpoint")
        assert str(addr) == "test-endpoint"


class TestListenerClose:
    async def test_close_marks_listener_closed(self):
        session, _ = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        assert not ln._closed
        await ln.close()
        assert ln._closed

    async def test_close_sends_go_away_frame(self):
        session, _ = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        await ln.close()
        session._send_frame.assert_awaited_once()
        frame = session._send_frame.call_args[0][0]
        from octobot_tunnel.yamux.constants import FRAME_TYPE_GO_AWAY
        assert frame.frame_type == FRAME_TYPE_GO_AWAY

    async def test_shutdown_closes_session(self):
        session, _ = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        await ln.shutdown()
        session.close.assert_awaited_once()
        assert ln._closed

    async def test_close_is_idempotent(self):
        session, _ = make_mock_session()
        upstream = make_mock_upstream()
        ln = Listener("ep", upstream)
        ln._attach_session(session)

        await ln.close()
        await ln.close()
        # Should not raise; send_frame called only once
        assert session._send_frame.await_count == 1
