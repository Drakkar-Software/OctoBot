#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import os

# tailscale-py (tailscale-rs bindings) requires this env var to acknowledge it is
# experimental, unaudited software. Must be set before the native module is imported.
os.environ.setdefault("TS_RS_EXPERIMENT", "this_is_unstable_software")

import tailscale

from .abstract_tunnel_backend import AbstractTunnelBackend

# tailscale-rs' Python binding does not currently expose Funnel/Serve: only the private
# tailnet can be reached, not the public internet. Flip this once tailscale-rs adds support.
# TODO: replace with the real libtailscale funnel call when tailscale-rs ships it.
_FUNNEL_SUPPORTED = False

_PUMP_CHUNK_SIZE = 65536


class TailscaleBackend(AbstractTunnelBackend):
    """
    Exposes one or more local (host, port) targets on the tailnet through a single
    connected device. Call open() once per target (e.g. once for the webhook server,
    once for the web interface): they all share the same tailscale.connect() session.
    """

    def __init__(self, auth_key: str, hostname: str, state_file: str):
        super().__init__()
        self.auth_key = auth_key
        self.hostname = hostname
        self.state_file = state_file
        self.device = None
        self._listeners = []  # list of (listener, accept_task)
        self._pump_tasks = set()

    async def _ensure_connected(self):
        if self.device is None:
            self.device = await tailscale.connect(
                self.state_file, self.auth_key, hostname=self.hostname
            )
        return self.device

    async def open(self, local_host: str, local_port: int) -> str:
        device = await self._ensure_connected()
        tailnet_ip = await device.ipv4_addr()
        listener = await device.tcp_listen((tailnet_ip, local_port))
        accept_task = asyncio.ensure_future(self._accept_loop(listener, local_host, local_port))
        self._listeners.append((listener, accept_task))
        return f"http://{tailnet_ip}:{local_port}"

    async def open_funnel(self, local_host: str, local_port: int) -> str:
        """
        Publicly expose (local_host, local_port) through Tailscale Funnel.
        Not supported by tailscale-py yet: returns a mock URL so callers can wire the
        integration ahead of upstream support, without crashing.
        """
        assert not _FUNNEL_SUPPORTED  # pragma: no cover - flip once tailscale-rs ships funnel
        self.logger.warning(
            "Tailscale Funnel is not yet supported by tailscale-py: returning a mock "
            "public URL. The webhook will only be reachable from the tailnet."
        )
        mock_hostname = self.hostname or "octobot"
        return f"https://{mock_hostname}.mock-tailnet.ts.net"

    async def _accept_loop(self, listener, local_host: str, local_port: int) -> None:
        try:
            while True:
                stream = await listener.accept()
                task = asyncio.ensure_future(self._pump(stream, local_host, local_port))
                self._pump_tasks.add(task)
                task.add_done_callback(self._pump_tasks.discard)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            self.logger.exception(err, True, f"Error in tailscale accept loop: {err}")

    async def _pump(self, stream, local_host: str, local_port: int) -> None:
        # Bridge bytes between the tailnet userspace TcpStream (no real fd) and a real
        # localhost TCP connection to the already-running local server (webhook or web UI).
        writer = None
        try:
            reader, writer = await asyncio.open_connection(local_host, local_port)
            await asyncio.gather(
                self._pump_to_local(stream, writer),
                self._pump_to_tailnet(stream, reader),
            )
        except Exception as err:
            self.logger.warning(f"Error while bridging tailscale connection: {err}")
        finally:
            if writer is not None:
                writer.close()

    @staticmethod
    async def _pump_to_local(stream, writer) -> None:
        while True:
            data = await stream.recv()
            if not data:
                break
            writer.write(data)
            await writer.drain()

    @staticmethod
    async def _pump_to_tailnet(stream, reader) -> None:
        while True:
            data = await reader.read(_PUMP_CHUNK_SIZE)
            if not data:
                break
            await stream.send(data)

    async def close(self) -> None:
        for _, accept_task in self._listeners:
            accept_task.cancel()
        for task in self._pump_tasks:
            task.cancel()
        self._listeners.clear()
        self._pump_tasks.clear()
        self.device = None
