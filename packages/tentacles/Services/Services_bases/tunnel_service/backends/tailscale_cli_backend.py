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
import json
import shutil

from .abstract_tunnel_backend import AbstractTunnelBackend
from .. import errors

_TAILSCALE_BIN = "tailscale"


class TailscaleCliBackend(AbstractTunnelBackend):
    """
    Exposes local (host, port) targets on the tailnet by shelling out to the `tailscale`
    CLI instead of tailscale-py. Requires the `tailscale` binary to be available in PATH
    (see is_available()) and its background daemon (tailscaled) reachable.

    Unlike TailscaleBackend (tailscale-py's userspace-only netstack, whose TcpStream has
    no real fd), `tailscale serve`/`tailscale funnel` are handled by the OS-level
    tailscaled daemon: no manual byte-pumping bridge is needed, and Funnel is genuinely
    supported here instead of returning a mock URL.
    """

    def __init__(self, auth_key: str, hostname: str):
        super().__init__()
        self.auth_key = auth_key
        self.hostname = hostname
        self._served = False
        self._funneled = False

    @staticmethod
    def is_available() -> bool:
        return shutil.which(_TAILSCALE_BIN) is not None

    async def _run(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            _TAILSCALE_BIN, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise errors.TunnelBackendUnavailableError(
                f"`tailscale {' '.join(args)}` failed: {stderr.decode().strip()}"
            )
        return stdout.decode().strip()

    async def _get_status(self) -> dict:
        return json.loads(await self._run("status", "--json"))

    async def _ensure_connected(self) -> dict:
        status = await self._get_status()
        if status.get("BackendState") != "Running":
            up_args = ["up"]
            if self.auth_key:
                up_args.append(f"--authkey={self.auth_key}")
            if self.hostname:
                up_args.append(f"--hostname={self.hostname}")
            await self._run(*up_args)
            status = await self._get_status()
        return status

    async def _get_dns_name(self) -> str:
        status = await self._ensure_connected()
        return status["Self"]["DNSName"].rstrip(".")

    async def open(self, local_host: str, local_port: int) -> str:
        dns_name = await self._get_dns_name()
        # positional-port syntax matches tailscale CLI >= 1.66; older CLIs use
        # `tailscale serve https:443 / http://host:port` instead.
        await self._run("serve", "--bg", f"http://{local_host}:{local_port}")
        self._served = True
        return f"https://{dns_name}"

    async def open_funnel(self, local_host: str, local_port: int) -> str:
        dns_name = await self._get_dns_name()
        await self._run("funnel", "--bg", f"http://{local_host}:{local_port}")
        self._funneled = True
        return f"https://{dns_name}"

    async def close(self) -> None:
        if self._served or self._funneled:
            await self._safe_run("serve", "reset")
            self._served = False
            self._funneled = False

    async def _safe_run(self, *args: str) -> None:
        try:
            await self._run(*args)
        except errors.TunnelBackendUnavailableError as err:
            self.logger.warning(f"Error while resetting tailscale CLI state: {err}")
