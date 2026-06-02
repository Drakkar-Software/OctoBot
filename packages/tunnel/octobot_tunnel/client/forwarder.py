import asyncio

from octobot_tunnel.client.exceptions import ConnectionClosed
from octobot_tunnel.client.listener import Listener
from octobot_tunnel.client.logger import Logger, NopLogger


class Forwarder:
    """
    Accepts connections from a Listener and forwards them to a local address.

    Each accepted stream is transparently bridged (bidirectional copy) to a
    fresh TCP connection at `addr`. Runs entirely in asyncio background tasks.

    Equivalent to the Go client's Forwarder struct.
    """

    def __init__(self, listener: Listener, addr: str, logger: Logger | None = None):
        self._listener = listener
        self._addr = addr
        self._log = logger or NopLogger()
        self._tasks: set[asyncio.Task] = set()
        self._done = asyncio.Event()
        self._accept_task = asyncio.ensure_future(self._accept_loop())

    async def wait(self) -> None:
        """Block until the forwarder has stopped."""
        await self._done.wait()

    async def close(self) -> None:
        """Stop accepting new connections and cancel all active forwarding tasks."""
        await self._listener.close()
        if not self._accept_task.done():
            self._accept_task.cancel()
            try:
                await self._accept_task
            except (asyncio.CancelledError, Exception):
                pass
        for t in list(self._tasks):
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._done.set()

    async def _accept_loop(self) -> None:
        try:
            while True:
                try:
                    stream = await self._listener.accept()
                except ConnectionClosed:
                    break
                task = asyncio.ensure_future(self._forward(stream))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
        except asyncio.CancelledError:
            pass
        finally:
            self._done.set()

    async def _forward(self, stream) -> None:
        host, port = self._parse_addr(self._addr)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except Exception as exc:
            self._log.error("failed to connect to local service", addr=self._addr, error=str(exc))
            await stream.close()
            return

        async def copy_stream_to_tcp():
            try:
                while True:
                    data = await stream.read(65536)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except Exception:
                pass
            finally:
                # Half-close: signal EOF to the server while keeping read side open
                try:
                    writer.write_eof()
                except Exception:
                    pass

        async def copy_tcp_to_stream():
            try:
                while True:
                    data = await reader.read(65536)
                    if not data:
                        break
                    await stream.write(data)
            except Exception:
                pass
            finally:
                try:
                    await stream.close()
                except Exception:
                    pass

        await asyncio.gather(copy_stream_to_tcp(), copy_tcp_to_stream(), return_exceptions=True)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    @staticmethod
    def _parse_addr(addr: str) -> tuple[str, int]:
        if ":" in addr:
            host, port_str = addr.rsplit(":", 1)
            return host or "localhost", int(port_str)
        return addr, 80
