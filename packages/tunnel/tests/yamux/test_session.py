import asyncio
import struct
import pytest

from octobot_tunnel.yamux.constants import (
    HEADER_FORMAT,
    YAMUX_VERSION,
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FRAME_TYPE_PING,
    FRAME_TYPE_GO_AWAY,
    FLAG_SYN,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_RST,
    GO_AWAY_NORMAL,
    DEFAULT_WINDOW_SIZE,
)
from octobot_tunnel.yamux.frame import Frame
from octobot_tunnel.yamux.session import YamuxSession

pytestmark = pytest.mark.asyncio


class InMemoryTransport:
    """Fake transport backed by asyncio queues for test injection."""

    def __init__(self):
        self._inbox: asyncio.Queue[bytes] = asyncio.Queue()
        self._outbox: asyncio.Queue[bytes] = asyncio.Queue()
        self._buf = b""
        self.closed = False

    async def read_exactly(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = await self._inbox.get()
            if chunk == b"":
                raise asyncio.IncompleteReadError(partial=self._buf, expected=n)
            self._buf += chunk
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    async def write(self, data: bytes) -> None:
        self._outbox.put_nowait(data)

    async def close(self) -> None:
        self.closed = True
        self._inbox.put_nowait(b"")  # unblock pending reads

    def inject(self, data: bytes) -> None:
        """Feed bytes as if they came from the network."""
        self._inbox.put_nowait(data)

    async def read_sent(self) -> bytes:
        """Read one chunk written by the session."""
        return await asyncio.wait_for(self._outbox.get(), timeout=1.0)

    def inject_frame(self, frame: Frame) -> None:
        self.inject(frame.encode())


def make_syn_frame(stream_id: int, data: bytes = b"") -> Frame:
    return Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_SYN, stream_id=stream_id, data=data)


def make_window_syn_frame(stream_id: int) -> Frame:
    return Frame(frame_type=FRAME_TYPE_WINDOW_UPDATE, flags=FLAG_SYN, stream_id=stream_id, length=0)


async def make_session():
    transport = InMemoryTransport()
    session = YamuxSession(transport)
    session.start()
    return session, transport


class TestYamuxSessionAccept:
    async def test_accept_returns_stream_on_data_syn(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        assert stream.stream_id == 2
        await session.close()

    async def test_accept_returns_stream_on_window_syn(self):
        session, transport = await make_session()
        transport.inject_frame(make_window_syn_frame(stream_id=4))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        assert stream.stream_id == 4
        await session.close()

    async def test_accept_with_initial_data(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2, data=b"first chunk"))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        data = await asyncio.wait_for(stream.read(1024), timeout=1.0)
        assert data == b"first chunk"
        await session.close()

    async def test_multiple_streams_accepted(self):
        session, transport = await make_session()
        for sid in (2, 4, 6):
            transport.inject_frame(make_syn_frame(stream_id=sid))
        streams = []
        for _ in range(3):
            s = await asyncio.wait_for(session.accept(), timeout=1.0)
            streams.append(s)
        assert {s.stream_id for s in streams} == {2, 4, 6}
        await session.close()


class TestYamuxSessionData:
    async def test_data_dispatched_to_correct_stream(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        transport.inject_frame(make_syn_frame(stream_id=4))
        s2 = await asyncio.wait_for(session.accept(), timeout=1.0)
        s4 = await asyncio.wait_for(session.accept(), timeout=1.0)

        transport.inject_frame(Frame(FRAME_TYPE_DATA, 0, 2, data=b"for stream 2"))
        transport.inject_frame(Frame(FRAME_TYPE_DATA, 0, 4, data=b"for stream 4"))

        d2 = await asyncio.wait_for(s2.read(1024), timeout=1.0)
        d4 = await asyncio.wait_for(s4.read(1024), timeout=1.0)
        assert d2 == b"for stream 2"
        assert d4 == b"for stream 4"
        await session.close()

    async def test_fin_causes_eof_on_stream(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        transport.inject_frame(Frame(FRAME_TYPE_DATA, FLAG_FIN, 2, data=b""))
        data = await asyncio.wait_for(stream.read(1024), timeout=1.0)
        assert data == b""
        await session.close()

    async def test_rst_raises_on_stream_read(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        transport.inject_frame(Frame(FRAME_TYPE_DATA, FLAG_RST, 2, data=b""))
        with pytest.raises(ConnectionError):
            await asyncio.wait_for(stream.read(1024), timeout=1.0)
        await session.close()


class TestYamuxSessionWindowUpdate:
    async def test_window_update_increases_stream_send_window(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        original = stream._send_window
        transport.inject_frame(Frame(FRAME_TYPE_WINDOW_UPDATE, 0, 2, length=4096))
        await asyncio.sleep(0.05)
        assert stream._send_window == original + 4096
        await session.close()

    async def test_fin_window_update_causes_eof(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        stream = await asyncio.wait_for(session.accept(), timeout=1.0)
        transport.inject_frame(Frame(FRAME_TYPE_WINDOW_UPDATE, FLAG_FIN, 2, length=0))
        data = await asyncio.wait_for(stream.read(1024), timeout=1.0)
        assert data == b""
        await session.close()


class TestYamuxSessionPing:
    async def test_ping_triggers_ack_response(self):
        session, transport = await make_session()
        ping = Frame(FRAME_TYPE_PING, FLAG_SYN, 0, length=12345)
        transport.inject_frame(ping)
        raw = await transport.read_sent()
        resp = Frame.decode(raw)
        assert resp.frame_type == FRAME_TYPE_PING
        assert resp.flags & FLAG_ACK
        assert resp.length == 12345
        await session.close()

    async def test_ping_ack_is_not_echoed(self):
        session, transport = await make_session()
        ack = Frame(FRAME_TYPE_PING, FLAG_ACK, 0, length=42)
        transport.inject_frame(ack)
        await asyncio.sleep(0.05)
        assert transport._outbox.empty()
        await session.close()


class TestYamuxSessionGoAway:
    async def test_go_away_closes_all_streams(self):
        session, transport = await make_session()
        transport.inject_frame(make_syn_frame(stream_id=2))
        transport.inject_frame(make_syn_frame(stream_id=4))
        s2 = await asyncio.wait_for(session.accept(), timeout=1.0)
        s4 = await asyncio.wait_for(session.accept(), timeout=1.0)

        transport.inject_frame(Frame(FRAME_TYPE_GO_AWAY, 0, 0, length=GO_AWAY_NORMAL))
        await asyncio.sleep(0.05)

        d2 = await asyncio.wait_for(s2.read(1024), timeout=1.0)
        d4 = await asyncio.wait_for(s4.read(1024), timeout=1.0)
        assert d2 == b""
        assert d4 == b""

    async def test_session_close_sends_go_away(self):
        session, transport = await make_session()
        await session.close()
        raw = await transport.read_sent()
        frame = Frame.decode(raw)
        assert frame.frame_type == FRAME_TYPE_GO_AWAY
        assert frame.length == GO_AWAY_NORMAL

    async def test_session_is_closed_after_close(self):
        session, transport = await make_session()
        await session.close()
        assert session._closed

    async def test_transport_is_closed_after_session_close(self):
        session, transport = await make_session()
        await session.close()
        assert transport.closed


class TestYamuxSessionConcurrency:
    async def test_concurrent_streams(self):
        session, transport = await make_session()
        num_streams = 10
        for i in range(num_streams):
            transport.inject_frame(make_syn_frame(stream_id=i * 2 + 2))

        streams = []
        for _ in range(num_streams):
            s = await asyncio.wait_for(session.accept(), timeout=1.0)
            streams.append(s)
        assert len(streams) == num_streams
        await session.close()

    async def test_data_frame_for_unknown_stream_is_ignored(self):
        session, transport = await make_session()
        transport.inject_frame(Frame(FRAME_TYPE_DATA, 0, 999, data=b"orphan"))
        await asyncio.sleep(0.05)
        assert not session._closed
        await session.close()
