import asyncio
from typing import Callable, Awaitable

from octobot_tunnel.yamux.constants import (
    HEADER_SIZE,
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FRAME_TYPE_PING,
    FRAME_TYPE_GO_AWAY,
    FLAG_SYN,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_RST,
    GO_AWAY_NORMAL,
    DEFAULT_ACCEPT_BACKLOG,
)
from octobot_tunnel.yamux.frame import Frame
from octobot_tunnel.yamux.stream import YamuxStream


class YamuxSession:
    """
    Client-side yamux session.

    The Piko server opens new streams (SYN) so we expose accept() to receive them.
    The transport must implement:
        async read_exactly(n: int) -> bytes
        async write(data: bytes) -> None
        async close() -> None
    """

    def __init__(self, transport):
        self._transport = transport
        self._streams: dict[int, YamuxStream] = {}
        self._accept_queue: asyncio.Queue[YamuxStream] = asyncio.Queue(maxsize=DEFAULT_ACCEPT_BACKLOG)
        self._closed = False
        self._close_event = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._read_task: asyncio.Task | None = None

    def start(self) -> None:
        self._read_task = asyncio.ensure_future(self._read_loop())

    async def accept(self) -> YamuxStream:
        if self._closed and self._accept_queue.empty():
            raise ConnectionError("session is closed")
        stream = await self._accept_queue.get()
        if stream is None:
            raise ConnectionError("session is closed")
        return stream

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._close_event.set()
        frame = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_NORMAL)
        try:
            await self._send_frame(frame)
        except Exception:
            pass
        await self._transport.close()
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except (asyncio.CancelledError, Exception):
                pass
        self._drain_accept_queue()

    async def send_go_away(self) -> None:
        """Send a GoAway frame without closing the session (used by Listener.close())."""
        frame = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_NORMAL)
        await self._send_frame(frame)

    async def _send_frame(self, frame: Frame) -> None:
        async with self._send_lock:
            await self._transport.write(frame.encode())

    def _drain_accept_queue(self) -> None:
        while not self._accept_queue.empty():
            try:
                self._accept_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def _read_loop(self) -> None:
        try:
            while not self._closed:
                raw_header = await self._transport.read_exactly(HEADER_SIZE)
                frame = Frame.decode(raw_header)
                if frame.frame_type == FRAME_TYPE_DATA:
                    if frame.length > 0:
                        payload = await self._transport.read_exactly(frame.length)
                        frame = Frame(
                            frame_type=FRAME_TYPE_DATA,
                            flags=frame.flags,
                            stream_id=frame.stream_id,
                            data=payload,
                            length=frame.length,
                        )
                    await self._handle_data(frame)
                elif frame.frame_type == FRAME_TYPE_WINDOW_UPDATE:
                    await self._handle_window_update(frame)
                elif frame.frame_type == FRAME_TYPE_PING:
                    await self._handle_ping(frame)
                elif frame.frame_type == FRAME_TYPE_GO_AWAY:
                    await self._handle_go_away(frame)
        except asyncio.IncompleteReadError:
            pass
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            self._closed = True
            self._close_event.set()
            for stream in list(self._streams.values()):
                stream.feed_eof()
            self._drain_accept_queue()
            # Wake any coroutine blocked in accept() so it can raise ConnectionError
            try:
                self._accept_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def _handle_data(self, frame: Frame) -> None:
        stream = self._streams.get(frame.stream_id)
        if frame.flags & FLAG_SYN:
            stream = YamuxStream(frame.stream_id, self)
            self._streams[frame.stream_id] = stream
            if frame.data:
                stream.feed_data(frame.data)
            try:
                self._accept_queue.put_nowait(stream)
            except asyncio.QueueFull:
                # Backlog exceeded — reset the stream
                await stream.reset()
                return
        elif stream is None:
            return
        else:
            if frame.data:
                stream.feed_data(frame.data)
            if frame.flags & FLAG_FIN:
                stream.feed_eof()
            if frame.flags & FLAG_RST:
                stream.feed_rst()

    async def _handle_window_update(self, frame: Frame) -> None:
        if frame.flags & FLAG_SYN:
            # Server opened a new stream with no initial data
            stream = YamuxStream(frame.stream_id, self)
            self._streams[frame.stream_id] = stream
            try:
                self._accept_queue.put_nowait(stream)
            except asyncio.QueueFull:
                await stream.reset()
            return
        if frame.flags & FLAG_FIN:
            stream = self._streams.get(frame.stream_id)
            if stream:
                stream.feed_eof()
            return
        stream = self._streams.get(frame.stream_id)
        if stream:
            stream.update_send_window(frame.length)

    async def _handle_ping(self, frame: Frame) -> None:
        if not (frame.flags & FLAG_ACK):
            # Echo back with ACK
            ack = Frame(frame_type=FRAME_TYPE_PING, flags=FLAG_ACK, stream_id=0, length=frame.length)
            await self._send_frame(ack)

    async def _handle_go_away(self, frame: Frame) -> None:
        self._closed = True
        self._close_event.set()
        for stream in list(self._streams.values()):
            stream.feed_eof()
        self._drain_accept_queue()
