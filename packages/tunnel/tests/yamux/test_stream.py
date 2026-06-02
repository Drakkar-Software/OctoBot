import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from octobot_tunnel.yamux.constants import (
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FLAG_FIN,
    FLAG_RST,
    DEFAULT_WINDOW_SIZE,
)
from octobot_tunnel.yamux.frame import Frame
from octobot_tunnel.yamux.stream import YamuxStream

pytestmark = pytest.mark.asyncio


def make_stream(stream_id=1):
    session = MagicMock()
    sent_frames = []

    async def capture_frame(frame):
        sent_frames.append(frame)

    session._send_frame = capture_frame
    stream = YamuxStream(stream_id, session)
    return stream, sent_frames


class TestYamuxStreamRead:
    async def test_read_returns_fed_data(self):
        stream, _ = make_stream()
        stream.feed_data(b"hello")
        data = await stream.read(1024)
        assert data == b"hello"

    async def test_read_blocks_until_data_available(self):
        stream, _ = make_stream()

        async def feeder():
            await asyncio.sleep(0.01)
            stream.feed_data(b"delayed")

        asyncio.ensure_future(feeder())
        data = await asyncio.wait_for(stream.read(1024), timeout=1.0)
        assert data == b"delayed"

    async def test_read_returns_empty_on_eof(self):
        stream, _ = make_stream()
        stream.feed_eof()
        data = await stream.read(1024)
        assert data == b""

    async def test_read_multiple_chunks(self):
        stream, _ = make_stream()
        stream.feed_data(b"abc")
        stream.feed_data(b"def")
        data1 = await stream.read(3)
        data2 = await stream.read(3)
        assert data1 == b"abc"
        assert data2 == b"def"

    async def test_read_raises_on_rst(self):
        stream, _ = make_stream()
        stream.feed_rst()
        with pytest.raises(ConnectionError):
            await stream.read(1024)


class TestYamuxStreamWrite:
    async def test_write_sends_data_frame(self):
        stream, sent = make_stream(stream_id=3)
        await stream.write(b"hello world")
        assert len(sent) >= 1
        frame = sent[0]
        assert frame.frame_type == FRAME_TYPE_DATA
        assert frame.data == b"hello world"
        assert frame.stream_id == 3

    async def test_write_respects_send_window(self):
        stream, sent = make_stream(stream_id=1)
        # Exhaust the window
        stream._send_window = 5

        write_done = asyncio.Event()

        async def writer():
            await stream.write(b"AB")  # 2 bytes, fits in window=5
            await stream.write(b"CDE")  # 3 bytes, exactly fills remaining window
            write_done.set()
            # This call should block until window is updated
            await stream.write(b"FGHI")

        task = asyncio.ensure_future(writer())
        await asyncio.wait_for(write_done.wait(), timeout=1.0)
        # Now unblock by updating the window
        stream.update_send_window(10)
        await asyncio.wait_for(task, timeout=1.0)
        total_sent = b"".join(f.data for f in sent if f.frame_type == FRAME_TYPE_DATA)
        assert total_sent == b"ABCDEFGHI"

    async def test_write_after_close_raises(self):
        stream, _ = make_stream()
        await stream.close()
        with pytest.raises(ConnectionError):
            await stream.write(b"data")

    async def test_write_empty_bytes_is_noop(self):
        stream, sent = make_stream()
        await stream.write(b"")
        data_frames = [f for f in sent if f.frame_type == FRAME_TYPE_DATA]
        assert len(data_frames) == 0


class TestYamuxStreamClose:
    async def test_close_sends_fin_frame(self):
        stream, sent = make_stream(stream_id=7)
        await stream.close()
        assert any(f.frame_type == FRAME_TYPE_DATA and f.flags & FLAG_FIN for f in sent)

    async def test_close_marks_stream_closed(self):
        stream, _ = make_stream()
        assert not stream.closed
        await stream.close()
        assert stream.closed

    async def test_close_is_idempotent(self):
        stream, sent = make_stream()
        await stream.close()
        await stream.close()
        fin_frames = [f for f in sent if f.flags & FLAG_FIN]
        assert len(fin_frames) == 1

    async def test_reset_sends_rst_frame(self):
        stream, sent = make_stream(stream_id=5)
        await stream.reset()
        assert any(f.frame_type == FRAME_TYPE_DATA and f.flags & FLAG_RST for f in sent)


class TestYamuxStreamWindowUpdate:
    async def test_window_update_sent_on_read(self):
        stream, sent = make_stream(stream_id=2)
        stream.feed_data(b"hello")
        await stream.read(5)
        # Should have sent a WINDOW_UPDATE for the 5 bytes consumed
        wu_frames = [f for f in sent if f.frame_type == FRAME_TYPE_WINDOW_UPDATE]
        assert len(wu_frames) == 1
        assert wu_frames[0].length == 5

    async def test_update_send_window_unblocks_write(self):
        stream, sent = make_stream()
        stream._send_window = 0
        stream._send_window_event.clear()

        write_done = asyncio.Event()

        async def writer():
            await stream.write(b"x")
            write_done.set()

        asyncio.ensure_future(writer())
        await asyncio.sleep(0.01)
        assert not write_done.is_set()
        stream.update_send_window(10)
        await asyncio.wait_for(write_done.wait(), timeout=1.0)
        assert write_done.is_set()
