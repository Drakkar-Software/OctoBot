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
from typing import Any, Optional

from starfish_sdk import StarfishClient, SyncManager
from starfish_sdk.types import ConflictResolver
from starfish_protocol.types import PushSuccess

import octobot_commons.logging as logging
import octobot_sync.auth as auth
import octobot_sync.constants as constants
import octobot_sync.crypto as crypto


def create_sync_client(
    private_key: str,
    sync_url: str = None,
) -> tuple[StarfishClient, str]:
    """Build a StarfishClient authenticated by a cap-cert derived from the EVM wallet.

    Returns ``(client, user_id)`` where ``user_id`` is the Starfish storage
    identity (``sha256(rootEdPub)[:32]``) the wallet derives to — used to build
    ``users/{identity}/...`` paths. The cap provider signs every request.
    """
    cap_provider = auth.WalletCapProvider(private_key)

    base_url = f"{sync_url.rstrip('/')}/{constants.SYNC_MOUNT_PATH}" if sync_url else sync_url
    client = StarfishClient(
        base_url=base_url,
        cap_provider=cap_provider,
        namespace=constants.SYNC_NAMESPACE,
    )
    logging.get_logger("SyncClient").info(
        f"Sync client initialized (sync server: {base_url}, user_id: {cap_provider.user_id})"
    )
    return client, cap_provider.user_id


def generate_share_credentials() -> tuple[str, str]:
    """Return a (secret, salt) pair for a one-shot encrypted share."""
    return secrets.token_hex(32), secrets.token_hex(16)


def _share_encryptor(
    encryption_secret: str | None,
    encryption_salt: str | None,
    encryption_info: str,
) -> crypto.SecretEncryptor | None:
    """Build a SecretEncryptor for an encrypted share, or None for plaintext."""
    if encryption_secret is None:
        return None
    return crypto.SecretEncryptor(encryption_secret, encryption_salt or "", encryption_info)


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
) -> dict[str, Any] | None:
    """Push payload via starfish SyncManager.

    Pass encryption_secret + encryption_salt + encryption_info for end-to-end
    encryption; omit them for plaintext transport.
    Pass on_conflict to customize optimistic-concurrency merge (default: remote-wins deep merge).
    Returns the raw push result dict.
    """
    manager = SyncManager(
        client,
        pull_path,
        push_path,
        on_conflict=on_conflict,
        encryptor=_share_encryptor(encryption_secret, encryption_salt, encryption_info),
    )
    return await manager.push(payload)


async def append_payload(
    client: StarfishClient,
    *,
    push_path: str,
    payload: dict[str, Any],
    timestamp: Optional[int] = None,
) -> PushSuccess:
    return await client.append(push_path, payload, ts=timestamp)


async def pull_payload(
    client: StarfishClient,
    *,
    push_path: str,
    pull_path: str,
    encryption_secret: str | None = None,
    encryption_salt: str | None = None,
    encryption_info: str = constants.DEFAULT_ENCRYPTION_INFO,
) -> dict[str, Any]:
    """Pull payload via starfish SyncManager.

    Pass encryption_secret + encryption_salt + encryption_info to decrypt;
    omit them for plaintext transport.
    Returns the payload dict.
    """
    manager = SyncManager(
        client,
        pull_path,
        push_path,
        encryptor=_share_encryptor(encryption_secret, encryption_salt, encryption_info),
    )
    result = await manager.pull()
    return result.data
