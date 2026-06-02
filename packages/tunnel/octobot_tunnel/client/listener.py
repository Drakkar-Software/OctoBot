import asyncio
from dataclasses import dataclass

from octobot_tunnel.client.exceptions import ConnectionClosed
from octobot_tunnel.yamux.constants import FRAME_TYPE_GO_AWAY, GO_AWAY_NORMAL
from octobot_tunnel.yamux.frame import Frame
from octobot_tunnel.yamux.session import YamuxSession
from octobot_tunnel.yamux.stream import YamuxStream


@dataclass(frozen=True)
class PikoAddr:
    """Address of a Piko endpoint, analogous to Go's pikoAddr."""
    network: str = "tcp"
    address: str = ""  # endpoint_id

    def __str__(self) -> str:
        return self.address


class Listener:
    """
    Listens for incoming connections on a Piko endpoint.

    The listener owns a yamux client session over a single outbound WebSocket
    connection. The Piko server opens new yamux streams for each incoming
    connection. On session disconnect, AcceptWithContext automatically
    reconnects using the parent Upstream's backoff strategy.

    Equivalent to the Go client's Listener interface + listener struct.
    """

    def __init__(self, endpoint_id: str, upstream: "Upstream"):
        self._endpoint_id = endpoint_id
        self._upstream = upstream
        self._session: YamuxSession | None = None
        self._close_event = asyncio.Event()
        self._closed = False

    def _attach_session(self, session: YamuxSession) -> None:
        self._session = session

    def endpoint_id(self) -> str:
        return self._endpoint_id

    def addr(self) -> PikoAddr:
        return PikoAddr(network="tcp", address=self._endpoint_id)

    async def accept(self) -> YamuxStream:
        return await self.accept_with_context(self._close_event)

    async def accept_with_context(self, stop_event: asyncio.Event) -> YamuxStream:
        """
        Accept the next incoming stream, reconnecting on session dropout.

        Returns immediately if stop_event is already set.
        Raises ConnectionClosed when close() / shutdown() has been called.
        """
        while True:
            if self._closed or stop_event.is_set():
                raise ConnectionClosed("listener is closed")
            if self._session is None:
                raise ConnectionClosed("no active session")
            try:
                # Race: accept or stop_event
                accept_task = asyncio.ensure_future(self._session.accept())
                stop_task = asyncio.ensure_future(stop_event.wait())
                done, pending = await asyncio.wait(
                    {accept_task, stop_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

                if stop_task in done:
                    accept_task.cancel()
                    raise ConnectionClosed("listener is closed")

                return accept_task.result()
            except ConnectionClosed:
                raise
            except ConnectionError:
                if self._closed or stop_event.is_set():
                    raise ConnectionClosed("listener is closed")
                # Session disconnected — attempt reconnect
                self._upstream._logger().warning(
                    "listener disconnected, reconnecting",
                    endpoint_id=self._endpoint_id,
                )
                new_session = await self._upstream._connect(self._endpoint_id)
                self._session = new_session

    async def close(self) -> None:
        """
        Stop accepting new connections (GoAway), but leave established
        yamux streams open — matching Go's Listener.Close().
        """
        if self._closed:
            return
        self._closed = True
        self._close_event.set()
        if self._session:
            # GoAway — tell server we're done accepting without tearing down streams
            try:
                frame = Frame(frame_type=FRAME_TYPE_GO_AWAY, flags=0, stream_id=0, length=GO_AWAY_NORMAL)
                await self._session._send_frame(frame)
            except Exception:
                pass

    async def shutdown(self) -> None:
        """Close the underlying yamux session (all streams terminated)."""
        self._closed = True
        self._close_event.set()
        if self._session:
            await self._session.close()
