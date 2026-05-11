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

import os
import secrets
import json
from collections.abc import Awaitable, Callable

from starfish_server.config.schema import SyncConfig
from starfish_server.storage.base import AbstractObjectStore
from starfish_server.storage.s3 import S3ObjectStore, S3StorageOptions
from starfish_server.storage.filesystem import FilesystemObjectStore, FilesystemStorageOptions

import octobot_commons.configuration as commons_configuration
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_sync.app as sync_app
import octobot_sync.auth as auth


_get_data: Callable[[str], Awaitable[str | None]] | None = None
_put_data: Callable[[str, str], Awaitable[None]] | None = None

AUTOMATIONS_STATE_KEY = "automations_state"
ACCOUNTS_STATE_KEY = "user-actions"

async def get_data(key: str) -> str | None:
    # called when client pulls
    import octobot_node.scheduler.api as scheduler_api
    if key == AUTOMATIONS_STATE_KEY:
        automations_state = await scheduler_api.get_automations_state(None)
        return json.dumps(
            automations_state.model_dump(mode="json")
        )
    elif key == ACCOUNTS_STATE_KEY:
        accounts_state = await scheduler_api.get_accounts_state()
        return json.dumps(
            accounts_state.model_dump(mode="json")
        )
    return None

async def put_data(key: str, body: str) -> None:
    # called when client pushes
    _get_logger().error(
        f"_put_data was called with ({key}, {body}). This is unexpected and should not happen."
    )

def set_data_callbacks(
    get_data: Callable[[str], Awaitable[str | None]],
    put_data: Callable[[str, str], Awaitable[None]],
) -> None:
    global _get_data, _put_data
    _get_data, _put_data = get_data, put_data


class _CallbackObjectStore(AbstractObjectStore):
    async def get_string(self, key: str) -> str | None:
        return await _get_data(key)  # type: ignore[misc]

    async def put(self, key: str, body: str, *, content_type: str | None = None, cache_control: str | None = None) -> None:
        await _put_data(key, body)  # type: ignore[misc]

    async def list_keys(self, prefix: str, *, start_after: str | None = None, limit: int | None = None) -> list[str]:
        return []

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def delete_many(self, keys: list[str]) -> None:
        raise NotImplementedError


def _get_logger():
    return logging.get_logger("OctoBot-Sync")


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {key}")
    return value


def build_object_store() -> AbstractObjectStore:
    if _get_data is not None and _put_data is not None:
        return _CallbackObjectStore()
    if os.environ.get("S3_ENDPOINT"):
        return S3ObjectStore(
            S3StorageOptions(
                access_key_id=_require_env("S3_ACCESS_KEY"),
                secret_access_key=_require_env("S3_SECRET_KEY"),
                endpoint=_require_env("S3_ENDPOINT"),
                bucket=_require_env("S3_BUCKET"),
                region=_require_env("S3_REGION"),
            )
        )
    data_dir = os.getenv("SYNC_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".octobot", "sync_data"
    )
    _get_logger().info(f"No S3_ENDPOINT configured, using filesystem storage at {data_dir}")
    return FilesystemObjectStore(FilesystemStorageOptions(base_dir=data_dir))


def get_or_generate_encryption_secret(config: commons_configuration.Configuration) -> str:
    env_secret = os.environ.get("ENCRYPTION_SECRET")
    if env_secret:
        return env_secret
    sync_section = config.config.get(commons_constants.CONFIG_SYNC) or {}
    secret = sync_section.get(commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET)
    if not secret:
        secret = secrets.token_hex(32)
        config.config.setdefault(commons_constants.CONFIG_SYNC, {})[
            commons_constants.CONFIG_SYNC_ENCRYPTION_SECRET
        ] = secret
        config.save()
        _get_logger().info("Generated new sync encryption secret and stored in config.json")
    return secret


def build_default_sync_app(
    is_allowed: Callable[[str], bool] | None = None,
    encryption_secret: str | None = None,
    sync_config: SyncConfig | None = None,
):
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())
    return sync_app.create_app(
        nonce,
        build_object_store(),
        is_allowed=is_allowed,
        encryption_secret=encryption_secret,
        sync_config=sync_config,
    )
