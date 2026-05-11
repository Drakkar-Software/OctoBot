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
from starfish_server.storage.base import AbstractObjectStore, StoreContext
from starfish_server.storage.s3 import S3ObjectStore, S3StorageOptions
from starfish_server.storage.filesystem import FilesystemObjectStore, FilesystemStorageOptions

import octobot_commons.configuration as commons_configuration
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.enums as enums
import octobot_sync.errors as errors

import octobot_protocol.models as protocol_models

import octobot_node.protocol.user_actions as user_actions_protocol
import octobot_node.protocol.user_data as user_data_protocol
import octobot_node.protocol.accounts as accounts_protocol


_get_data: Callable[[str, StoreContext | None], Awaitable[str | None]] | None = None
_put_data: Callable[[str, str, StoreContext | None], Awaitable[None]] | None = None


def _get_address(context: StoreContext | None) -> str:
    if context and context.identity:
        return context.identity
    raise errors.OctobotSyncIdentityMissingError("Identity is missing from the context")


async def get_data(key: str, context: StoreContext | None = None) -> str | None:
    # called when client pulls
    match key:
        case enums.Collections.USER_DATA.value:
            user_data_state = await user_data_protocol.get_user_data_state(
                _get_address(context)
            )
            return json.dumps(
                user_data_state.model_dump(mode="json")
            )
        case enums.Collections.USER_ACCOUNTS.value:
            accounts_state = accounts_protocol.get_accounts_state(
                _get_address(context)
            )
            return json.dumps(
                accounts_state.model_dump(mode="json")
            )
        case _:
            _get_logger().error(
                f"get_data was called with ({key}). This collection is not supported."
            )
            return None

async def put_data(key: str, body: str, context: StoreContext | None = None) -> None:
    match key:
        case enums.Collections.USER_ACTIONS.value:
            user_actions_state = protocol_models.UserActionsState.model_validate_json(body)
            if user_actions_state.user_actions:
                for action in user_actions_state.user_actions:
                    try:
                        await user_actions_protocol.execute_user_action(
                            action, _get_address(context)
                        )
                    except Exception as exc:
                        _get_logger().exception(
                            exc, True, f"Unexpected error executing user action: {action.id}: {exc}"
                        )
        case _:
            _get_logger().error(
                f"put_data was called with ({key}, {body}). This is unexpected and should not happen."
            )

def set_data_callbacks(
    get_data: Callable[[str, StoreContext | None], Awaitable[str | None]],
    put_data: Callable[[str, str, StoreContext | None], Awaitable[None]],
) -> None:
    global _get_data, _put_data
    _get_data, _put_data = get_data, put_data


class _CallbackObjectStore(AbstractObjectStore):
    async def get_string(self, key: str, *, context: StoreContext | None = None) -> str | None:
        return await _get_data(key, context)  # type: ignore[misc]

    async def put(self, key: str, body: str, *, content_type: str | None = None, cache_control: str | None = None, context: StoreContext | None = None) -> None:
        await _put_data(key, body, context)  # type: ignore[misc]

    async def list_keys(self, prefix: str, *, start_after: str | None = None, limit: int | None = None, context: StoreContext | None = None) -> list[str]:
        return []

    async def delete(self, key: str, *, context: StoreContext | None = None) -> None:
        raise NotImplementedError

    async def delete_many(self, keys: list[str], *, context: StoreContext | None = None) -> None:
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
