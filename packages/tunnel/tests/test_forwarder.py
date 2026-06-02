import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from octobot_tunnel.client.exceptions import ConnectionClosed
from octobot_tunnel.client.forwarder import Forwarder

pytestmark = pytest.mark.asyncio


def make_mock_stream(recv_data=b"", send_buf=None):
    stream = MagicMock()
    data_queue = asyncio.Queue()
    if recv_data:
        data_queue.put_nowait(recv_data)
    data_queue.put_nowait(b"")  # EOF sentinel

    async def read(n):
        return await data_queue.get()

    stream.read = read
    stream.write = AsyncMock()
    stream.close = AsyncMock()
    return stream


def make_mock_listener(streams=None, close_after_streams=True):
    """
    Create a mock Listener.

    If close_after_streams=True (default), accept() raises ConnectionClosed after
    all queued streams have been delivered.
    If close_after_streams=False, accept() blocks indefinitely when the queue is empty.
    """
    listener = MagicMock()
    q = asyncio.Queue()
    closed_event = asyncio.Event()
    if streams:
        for s in streams:
            q.put_nowait(s)

    call_count = [0]
    streams_delivered = [0]
    total_streams = len(streams) if streams else 0

    async def accept():
        call_count[0] += 1
        # If listener was externally closed, raise immediately
        if closed_event.is_set() and q.empty():
            raise ConnectionClosed("listener closed")
        if close_after_streams and q.empty():
            raise ConnectionClosed("no more streams")
        # Block until a stream is available or listener is closed
        while q.empty():
            if closed_event.is_set():
                raise ConnectionClosed("listener closed")
            await asyncio.sleep(0.01)
        s = await q.get()
        streams_delivered[0] += 1
        return s

    async def close():
        closed_event.set()

    listener.accept = accept
    listener.close = close
    return listener, q, call_count


class TestForwarderClose:
    async def test_wait_blocks_until_closed(self):
        listener, q, _ = make_mock_listener(close_after_streams=False)
        fwd = Forwarder(listener, "localhost:9000")

        wait_done = asyncio.Event()

        async def waiter():
            await fwd.wait()
            wait_done.set()

        asyncio.ensure_future(waiter())
        await asyncio.sleep(0.05)
        assert not wait_done.is_set()
        await fwd.close()
        await asyncio.wait_for(wait_done.wait(), timeout=1.0)

    async def test_close_stops_accept_loop(self):
        listener, q, call_count = make_mock_listener(close_after_streams=False)
        fwd = Forwarder(listener, "localhost:9000")
        await asyncio.sleep(0.02)
        await fwd.close()

    async def test_close_sets_done(self):
        listener, _, _ = make_mock_listener(close_after_streams=False)
        fwd = Forwarder(listener, "localhost:9000")
        await fwd.close()
        assert fwd._done.is_set()

    async def test_accept_loop_stops_on_connection_closed(self):
        # empty streams + close_after_streams=True → raises ConnectionClosed immediately
        listener, _, _ = make_mock_listener(streams=[], close_after_streams=True)
        fwd = Forwarder(listener, "localhost:9000")
        await asyncio.wait_for(fwd.wait(), timeout=1.0)


class TestForwarderForward:
    async def test_forward_copies_data_to_upstream(self):
        """Data from accepted stream reaches the local TCP server."""
        received = []

        async def echo_server(reader, writer):
            data = await reader.read(100)
            received.append(data)
            writer.close()

        server = await asyncio.start_server(echo_server, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        stream = make_mock_stream(recv_data=b"hello from piko")
        listener, q, _ = make_mock_listener(streams=[stream])
        fwd = Forwarder(listener, f"127.0.0.1:{port}")

        await asyncio.sleep(0.2)
        server.close()
        await server.wait_closed()
        await fwd.close()
        assert b"hello from piko" in received

    async def test_forward_copies_data_from_upstream(self):
        """Data sent by the local TCP server reaches the piko stream."""
        async def send_server(reader, writer):
            writer.write(b"server says hi")
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(send_server, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        stream = make_mock_stream(recv_data=b"")
        listener, q, _ = make_mock_listener(streams=[stream])
        fwd = Forwarder(listener, f"127.0.0.1:{port}")

        await asyncio.sleep(0.2)
        server.close()
        await server.wait_closed()
        await fwd.close()
        # stream.write should have been called with server data
        calls = [c.args[0] for c in stream.write.call_args_list]
        all_data = b"".join(calls)
        assert b"server says hi" in all_data

    async def test_forward_handles_connection_refused(self):
        """Forwarder doesn't crash when local address is unreachable."""
        stream = make_mock_stream(recv_data=b"data")
        listener, q, _ = make_mock_listener(streams=[stream])
        fwd = Forwarder(listener, "127.0.0.1:1")  # port 1 should be refused

        await asyncio.sleep(0.2)
        await fwd.close()
        stream.close.assert_awaited()


class TestForwarderParseAddr:
    def test_parse_host_port(self):
        host, port = Forwarder._parse_addr("myhost:9000")
        assert host == "myhost"
        assert port == 9000

    def test_parse_localhost(self):
        host, port = Forwarder._parse_addr("localhost:3000")
        assert host == "localhost"
        assert port == 3000

    def test_parse_ip(self):
        host, port = Forwarder._parse_addr("127.0.0.1:8080")
        assert host == "127.0.0.1"
        assert port == 8080

    def test_parse_no_port_defaults_80(self):
        host, port = Forwarder._parse_addr("myhost")
        assert port == 80
