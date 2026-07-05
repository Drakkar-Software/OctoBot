#  Drakkar-Software OctoBot-Interfaces
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
import os
import socket
import typing

import octobot_services.constants as services_constants
import tentacles.Services.Services_bases as Service_bases


def get_node_web_ui_url() -> typing.Optional[str]:
    node_api_service = Service_bases.NodeApiService.instance()
    if not Service_bases.NodeApiService.get_is_enabled(node_api_service.config):
        return None
    return f"{node_api_service.get_node_api_url().rstrip('/')}/app"


def get_node_local_endpoint() -> tuple[str, int]:
    node_api_service = Service_bases.NodeApiService.instance()
    port = node_api_service.get_bind_port()
    bind_address = os.getenv(services_constants.ENV_NODE_API_ADDRESS)
    if bind_address and bind_address not in ("0.0.0.0", "127.0.0.1"):
        local_ip = bind_address
    else:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            local_ip = "127.0.0.1"
    return local_ip, port
