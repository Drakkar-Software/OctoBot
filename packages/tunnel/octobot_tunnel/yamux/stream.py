import asyncio

from octobot_tunnel.yamux.constants import (
    FRAME_TYPE_DATA,
    FRAME_TYPE_WINDOW_UPDATE,
    FLAG_FIN,
    FLAG_RST,
    DEFAULT_WINDOW_SIZE,
)
from octobot_tunnel.yamux.frame import Frame


class YamuxStream:
    """
    A single bidirectional yamux stream.

    Receive side: backed by asyncio.StreamReader fed by the session read loop.
    Send side: writes DATA frames through the parent session, respecting the
    send-window set by the remote WINDOW_UPDATE frames.
    """

    def __init__(self, stream_id: int, session: "YamuxSession"):
        self._id = stream_id
        self._session = session
        self._reader: asyncio.StreamReader = asyncio.StreamReader()
        # How many bytes the remote side is willing to receive from us
        self._send_window = DEFAULT_WINDOW_SIZE
        self._send_window_event = asyncio.Event()
        self._send_window_event.set()
        self._send_lock = asyncio.Lock()
        self._closed = False
        self._remote_closed = False

    @property
    def stream_id(self) -> int:
        return self._id

    # ------------------------------------------------------------------
    # Receive side (called by the session read loop)
    # ------------------------------------------------------------------

    def feed_data(self, data: bytes) -> None:
        if data:
            self._reader.feed_data(data)

    def feed_eof(self) -> None:
        self._remote_closed = True
        self._reader.feed_eof()

    def feed_rst(self) -> None:
        exc = ConnectionError(f"stream {self._id} reset by remote")
        self._reader.set_exception(exc)
        self._closed = True

    def update_send_window(self, delta: int) -> None:
        self._send_window += delta
        if self._send_window > 0:
            self._send_window_event.set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def read(self, n: int = -1) -> bytes:
        if self._closed and self._reader.at_eof():
            return b""
        data = await self._reader.read(n)
        if data and not self._remote_closed:
            # Tell the sender it can send more
            await self._send_window_update(len(data))
        return data

    async def readexactly(self, n: int) -> bytes:
        return await self._reader.readexactly(n)

    async def write(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionError(f"stream {self._id} is closed")
        offset = 0
        async with self._send_lock:
            while offset < len(data):
                # Wait until we have send-window budget
                while self._send_window <= 0:
                    self._send_window_event.clear()
                    await self._send_window_event.wait()
                chunk_size = min(len(data) - offset, self._send_window, DEFAULT_WINDOW_SIZE)
                chunk = data[offset: offset + chunk_size]
                self._send_window -= len(chunk)
                frame = Frame(frame_type=FRAME_TYPE_DATA, flags=0, stream_id=self._id, data=chunk)
                await self._session._send_frame(frame)
                offset += len(chunk)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        frame = Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_FIN, stream_id=self._id, data=b"")
        await self._session._send_frame(frame)

    async def reset(self) -> None:
        if self._closed:
            return
        self._closed = True
        frame = Frame(frame_type=FRAME_TYPE_DATA, flags=FLAG_RST, stream_id=self._id, data=b"")
        await self._session._send_frame(frame)

    @property
    def closed(self) -> bool:
        return self._closed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send_window_update(self, delta: int) -> None:
        frame = Frame(
            frame_type=FRAME_TYPE_WINDOW_UPDATE,
            flags=0,
            stream_id=self._id,
            length=delta,
        )
        await self._session._send_frame(frame)
