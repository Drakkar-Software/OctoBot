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
import pyngrok.ngrok as ngrok

from .abstract_tunnel_backend import AbstractTunnelBackend


class NgrokBackend(AbstractTunnelBackend):
    def __init__(self, auth_token: str, domain: str = None):
        super().__init__()
        self.auth_token = auth_token
        self.domain = domain
        self.tunnel = None

    async def open(self, local_host: str, local_port: int) -> str:
        ngrok.set_auth_token(self.auth_token)
        self.tunnel = ngrok.connect(local_port, "http", domain=self.domain)
        return self.tunnel.public_url

    async def close(self) -> None:
        ngrok.kill()
        self.tunnel = None
