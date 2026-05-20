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
import typing
import secrets
import json
from collections.abc import Awaitable, Callable

from starfish_server.config.schema import SyncConfig
from starfish_server.protocol.types import DOCUMENT_VERSION
from starfish_server.storage.base import AbstractObjectStore, StoreContext
from starfish_server.storage.s3 import S3ObjectStore, S3StorageOptions
from starfish_server.storage.filesystem import FilesystemObjectStore, FilesystemStorageOptions

import octobot_commons.configuration as commons_configuration
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_commons.user_root_folder_provider as user_root_folder_provider
import octobot_node.constants as node_constants
import octobot.community.authentication as community_authentication
import octobot.community.wallet_backend.errors as wallet_backend_errors

import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.crypto as sync_crypto
import octobot_sync.enums as enums
import octobot_sync.errors as errors

import octobot_protocol.models as protocol_models

import octobot_node.protocol.user_actions as user_actions_protocol
import octobot_node.protocol.user_data as user_data_protocol
import octobot_node.protocol.accounts as accounts_protocol
import octobot_node.protocol.accounts_authentication as accounts_auth_protocol
import octobot_node.protocol.accounts_trading as accounts_trading_protocol


_get_data: Callable[[str, StoreContext | None], Awaitable[str | None]] | None = None
_put_data: Callable[[str, str, StoreContext | None], Awaitable[None]] | None = None


def _get_address(context: StoreContext | None) -> str:
    if context and context.identity:
        return context.identity
    raise errors.OctobotSyncIdentityMissingError("Identity is missing from the context")


def _get_collection(context: StoreContext | None) -> str:
    if context and context.collection:
        return context.collection
    raise errors.OctobotSyncCollectionMissingError("Collection is missing from the context")


def _get_account_id(context: StoreContext | None) -> str:
    if context and context.params.get("account_id"):
        return str(context.params["account_id"])
    raise errors.OctobotSyncAccountIdMissingError("account_id is missing from the context")


def _get_wallet_private_key(address: str) -> str:
    try:
        wallet = community_authentication.CommunityAuthentication.instance().get_wallet(address)
    except wallet_backend_errors.WalletNotFoundError as err:
        raise errors.OctobotSyncWalletNotFoundError(
            f"Wallet not found for address: {address}"
        ) from err
    return wallet.private_key


def _encrypt(data: str, address: str, collection: str) -> str:
    wallet_private_key = _get_wallet_private_key(address)
    return sync_crypto.encrypt_utf8_json_to_wire(data, wallet_private_key, collection)


def _decrypt(data: str, address: str, collection: str) -> str:
    wallet_private_key = _get_wallet_private_key(address)
    return sync_crypto.decrypt_wire_to_utf8_json(data, wallet_private_key, collection)


def _wrap_as_stored_document(encrypted_payload: str, plaintext_for_hash: str) -> str:
    """Wrap a server-encrypted payload in the StoredDocument shape that
    starfish_server.protocol.pull expects: ``{"v","data","timestamps","hash"}``.

    Hash is computed on the plaintext so it stays stable across calls — AES-GCM
    uses a random nonce, so hashing the ciphertext would change every pull and
    break ETag caching.
    """
    return json.dumps({
        "v": DOCUMENT_VERSION,
        "data": encrypted_payload,
        "timestamps": {},
        "hash": sync_crypto.sha256_hex(plaintext_for_hash),
    })


def _unwrap_stored_document_data(body: str) -> str:
    """Inverse of _wrap_as_stored_document for the push path: extract the
    encrypted payload from the StoredDocument wrapper the client sends.
    """
    parsed = json.loads(body)
    payload = parsed.get("data")
    if not isinstance(payload, str):
        raise errors.OctobotSyncError(
            f"Push body missing string 'data' field; got {type(payload).__name__}"
        )
    return payload


_opaque_store: FilesystemObjectStore | None = None


def _get_opaque_store() -> FilesystemObjectStore:
    global _opaque_store
    if _opaque_store is None:
        data_dir = os.path.join(
            user_root_folder_provider.get_user_root_folder(), "sync", "data"
        )
        _opaque_store = FilesystemObjectStore(
            FilesystemStorageOptions(base_dir=data_dir)
        )
    return _opaque_store


async def get_data(key: str, context: StoreContext | None = None) -> str | None:
    # called when client pulls
    collection = _get_collection(context)
    plaintext = None
    already_encrypted_payload = None
    match collection:
        case enums.Collections.USER_DATA.value:
            user_data_state = await user_data_protocol.get_user_data_state(
                _get_address(context)
            )
            plaintext = user_data_state.to_json()
        case enums.Collections.USER_ACCOUNTS.value:
            encrypted_blob = accounts_protocol.get_accounts_state_encrypted(
                _get_address(context)
            )
            already_encrypted_payload = json.dumps(encrypted_blob)
        case enums.Collections.USER_ACCOUNTS_AUTH.value:
            encrypted_blob = accounts_auth_protocol.get_accounts_authentication_state_encrypted(
                _get_address(context)
            )
            already_encrypted_payload = json.dumps(encrypted_blob)
        case enums.Collections.USER_ACCOUNTS_TRADING.value:
            encrypted_blob = accounts_trading_protocol.get_account_trading_state_encrypted(
                _get_address(context),
                _get_account_id(context),
            )
            already_encrypted_payload = json.dumps(encrypted_blob)
        case enums.Collections.USER_ACTIONS.value:
            # reading user actions should always return an empty list
            actions_state = protocol_models.UserActionsState(
                version=node_constants.USER_ACTIONS_STATE_VERSION,
                user_actions=[]
            )
            plaintext = actions_state.to_json()
        case _:
            # Opaque storage: collections with no protocol bridge are persisted
            # as client-encrypted ciphertext and the node never decrypts them.
            ciphertext = await _get_opaque_store().get_string(key)
            if ciphertext is None:
                return None
            # Stored bytes are already the client's ciphertext — hash them
            # directly so it stays stable until the next push overwrites it.
            return _wrap_as_stored_document(ciphertext, ciphertext)
    if already_encrypted_payload is not None:
        # Pre-encrypted payload (USER_ACCOUNTS): hash the encrypted JSON itself —
        # it is deterministic (read from disk) so the hash stays stable.
        return _wrap_as_stored_document(already_encrypted_payload, already_encrypted_payload)
    if plaintext is None:
        return None
    encrypted = _encrypt(plaintext, _get_address(context), collection)
    return _wrap_as_stored_document(encrypted, plaintext)

async def put_data(key: str, body: str, context: StoreContext | None = None) -> None:
    collection = _get_collection(context)
    match collection:
        case enums.Collections.USER_ACTIONS.value:
            encrypted_payload = _unwrap_stored_document_data(body)
            user_actions_state = protocol_models.UserActionsState.from_json(
                _decrypt(encrypted_payload, _get_address(context), collection)
            )
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
            # Opaque storage: persist the client ciphertext as-is. The node
            # never decrypts these collections — wallet-key decryption happens
            # entirely on the client.
            ciphertext = _unwrap_stored_document_data(body)
            await _get_opaque_store().put(key, ciphertext, content_type="application/json")

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
