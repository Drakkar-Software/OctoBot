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

import secrets
from typing import Any

from starfish_sdk import StarfishClient, SyncManager
from starfish_sdk.types import ConflictResolver

import octobot_commons.logging as logging
import octobot_sync.auth as auth
import octobot_sync.constants as constants


def create_sync_client(
    private_key: str,
    sync_url: str = None,
) -> tuple[StarfishClient, str, str]:
    auth_provider = auth.StarfishAuthProvider(private_key)

    base_url = f"{sync_url.rstrip('/')}/{constants.SYNC_MOUNT_PATH}" if sync_url else sync_url
    client = StarfishClient(
        base_url=base_url,
        auth=auth_provider,
        namespace=constants.SYNC_NAMESPACE,
    )
    logging.get_logger("SyncClient").info(
        f"Sync client initialized (sync server: {base_url}, address: {auth_provider.address})"
    )
    return client, auth_provider.address, auth_provider.sign_payload


def generate_share_credentials() -> tuple[str, str]:
    """Return a (secret, salt) pair for a one-shot encrypted share."""
    return secrets.token_hex(32), secrets.token_hex(16)


async def push_payload(
    client: StarfishClient,
    *,
    push_path: str,
    pull_path: str,
    payload: dict[str, Any],
    on_conflict: ConflictResolver | None = None,
    encryption_secret: str | None = None,
    encryption_salt: str | None = None,
    encryption_info: str = constants.DEFAULT_ENCRYPTION_INFO,
    sign_data=None,
) -> dict[str, Any] | None:
    """Push payload via starfish SyncManager.

    Pass encryption_secret + encryption_salt + encryption_info for end-to-end
    encryption; omit them for plaintext transport.
    Pass on_conflict to customize optimistic-concurrency merge (default: remote-wins deep merge).
    Returns the raw push result dict.
    """
    manager = SyncManager(
        client=client,
        pull_path=pull_path,
        push_path=push_path,
        on_conflict=on_conflict,
        encryption_secret=encryption_secret,
        encryption_salt=encryption_salt,
        encryption_info=encryption_info,
        sign_data=sign_data,
    )
    return await manager.push(payload)


async def pull_payload(
    client: StarfishClient,
    *,
    push_path: str,
    pull_path: str,
    encryption_secret: str | None = None,
    encryption_salt: str | None = None,
    encryption_info: str = constants.DEFAULT_ENCRYPTION_INFO,
    sign_data=None,
) -> dict[str, Any]:
    """Pull payload via starfish SyncManager.

    Pass encryption_secret + encryption_salt + encryption_info to decrypt;
    omit them for plaintext transport.
    Returns the payload dict.
    """
    manager = SyncManager(
        client=client,
        pull_path=pull_path,
        push_path=push_path,
        encryption_secret=encryption_secret,
        encryption_salt=encryption_salt,
        encryption_info=encryption_info,
        sign_data=sign_data,
    )
    result = await manager.pull()
    return result.data
