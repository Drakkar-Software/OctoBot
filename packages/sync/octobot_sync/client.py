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

from starfish_sdk import StarfishClient

import octobot_commons.logging as logging
import octobot_sync.auth as auth
import octobot_sync.server as server

_local_server_thread: threading.Thread | None = None


def create_sync_client(
    private_key: str,
    chain_id: str,
    sync_url: str = None,
    start_replica_server: bool = False,
    replica_port: int = 3000,
    replica_write_mode: str = "bidirectional",
    replica_sync_interval_ms: int = 60_000,
) -> tuple[StarfishClient, str]:
    auth_provider = auth.StarfishAuthProvider(private_key, chain_id)

    if start_replica_server:
        sync_url = _start_replica_server(
            primary_url=sync_url,
            private_key=private_key,
            chain_id=chain_id,
            port=replica_port,
            platform_pubkey=auth_provider.address,
            write_mode=replica_write_mode,
            sync_interval_ms=replica_sync_interval_ms,
        )

    client = StarfishClient(
        base_url=sync_url,
        auth=auth_provider,
    )
    logging.get_logger("SyncClient").info(f"Sync client initialized (sync server: {sync_url}, address: {auth_provider.address})")
    return client, auth_provider.address


def _start_replica_server(
    primary_url: str,
    private_key: str,
    chain_id: str,
    port: int,
    platform_pubkey: str,
    write_mode: str = "bidirectional",
    sync_interval_ms: int = 60_000,
) -> str:
    global _local_server_thread
    if _local_server_thread is None or not _local_server_thread.is_alive():
        _local_server_thread = server.start_replica_server_background(
            primary_url=primary_url,
            private_key=private_key,
            chain_id=chain_id,
            host="127.0.0.1",
            port=port,
            platform_pubkey=platform_pubkey,
            write_mode=write_mode,
            sync_interval_ms=sync_interval_ms,
        )
    return f"http://127.0.0.1:{port}"
