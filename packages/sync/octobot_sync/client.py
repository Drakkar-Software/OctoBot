#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import threading

from satellite_sdk import SatelliteClient

import octobot_commons.logging as logging
import octobot_sync.auth as auth
import octobot_sync.server as server

_local_server_thread: threading.Thread | None = None


def create_sync_client(
    private_key: str,
    chain_id: str,
    sync_url: str = None,
    start_local_server: bool = False,
    local_server_port: int = 3000,
) -> tuple[SatelliteClient, str]:
    auth_provider = auth.SatelliteAuthProvider(private_key, chain_id)

    if start_local_server:
        sync_url = _start_local_server(
            port=local_server_port,
            platform_pubkey=auth_provider.address,
        )

    client = SatelliteClient(
        base_url=sync_url,
        auth=auth_provider,
    )
    logging.get_logger("SyncClient").info(f"Sync client initialized (sync server: {sync_url}, address: {auth_provider.address})")
    return client, auth_provider.address


def _start_local_server(port: int, platform_pubkey: str) -> str:
    global _local_server_thread
    if _local_server_thread is None or not _local_server_thread.is_alive():
        _local_server_thread = server.start_sync_server_background(
            host="127.0.0.1",
            port=port,
            platform_pubkey=platform_pubkey,
        )
    return f"http://127.0.0.1:{port}"
