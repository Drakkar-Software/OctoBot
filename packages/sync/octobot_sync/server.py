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
import threading

import uvicorn
from starfish_server.storage.s3 import S3ObjectStore, S3StorageOptions
from starfish_server.storage.filesystem import FilesystemObjectStore, FilesystemStorageOptions

import octobot_commons.logging as logging
import octobot_sync.app as sync_app
import octobot_sync.auth as auth
import octobot_sync.chain as chain

def _get_logger():
    return logging.get_logger("OctoBot-Sync")


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {key}")
    return value


def _setup_registry() -> chain.ChainRegistry:
    registry = chain.ChainRegistry()
    evm_base_rpc = os.getenv("EVM_BASE_RPC")
    evm_contract_base = os.getenv("EVM_CONTRACT_BASE")
    if evm_base_rpc and evm_contract_base:
        registry.register(chain.EvmChain("evm:8453", evm_base_rpc, evm_contract_base))
    else:
        registry.register(chain.EvmChain("evm:8453"))
    return registry


def _build_app(platform_pubkey: str | None = None) -> tuple:
    """Build a standalone (primary) server backed by S3 storage."""
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())

    object_store = S3ObjectStore(
        S3StorageOptions(
            access_key_id=_require_env("S3_ACCESS_KEY"),
            secret_access_key=_require_env("S3_SECRET_KEY"),
            endpoint=_require_env("S3_ENDPOINT"),
            bucket=_require_env("S3_BUCKET"),
            region=_require_env("S3_REGION"),
        )
    )

    registry = _setup_registry()

    if platform_pubkey:
        os.environ.setdefault("PLATFORM_PUBKEY_EVM", platform_pubkey)

    app = sync_app.create_app(nonce, object_store, registry)
    return app


def _build_replica_app(
    primary_url: str,
    private_key: str,
    chain_id: str,
    platform_pubkey: str | None = None,
    write_mode: str = "bidirectional",
    sync_interval_ms: int = 60_000,
    data_dir: str | None = None,
) -> tuple:
    """Build a replica server backed by local filesystem storage."""
    nonce = auth.NonceStore(auth.MemoryStorageAdapter())

    resolved_data_dir = data_dir or os.path.join(
        os.path.expanduser("~"), ".octobot", "sync_data"
    )
    object_store = FilesystemObjectStore(
        FilesystemStorageOptions(base_dir=resolved_data_dir)
    )

    registry = _setup_registry()
    auth_provider = auth.StarfishAuthProvider(private_key, chain_id)

    if platform_pubkey:
        os.environ.setdefault("PLATFORM_PUBKEY_EVM", platform_pubkey)

    app = sync_app.create_app(
        nonce,
        object_store,
        registry,
        primary_url=primary_url,
        auth_provider=auth_provider,
        write_mode=write_mode,
        sync_interval_ms=sync_interval_ms,
    )
    return app


def start_sync_server(host: str = "0.0.0.0", port: int | None = None) -> None:
    app = _build_app()
    resolved_port = port or int(os.getenv("PORT", "3000"))
    _get_logger().info(f"OctoBot-Sync server listening on {host}:{resolved_port}")
    uvicorn.run(app, host=host, port=resolved_port)


def start_sync_server_background(
    host: str = "127.0.0.1",
    port: int = 3000,
    platform_pubkey: str | None = None,
) -> threading.Thread:
    app = _build_app(platform_pubkey=platform_pubkey)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="octobot-sync", daemon=True)
    thread.start()
    _get_logger().info(f"Local sync server started on http://{host}:{port}")
    return thread


def start_replica_server_background(
    primary_url: str,
    private_key: str,
    chain_id: str,
    host: str = "127.0.0.1",
    port: int = 3000,
    platform_pubkey: str | None = None,
    write_mode: str = "bidirectional",
    sync_interval_ms: int = 60_000,
    data_dir: str | None = None,
) -> threading.Thread:
    """Start a replica server in a background daemon thread."""
    app = _build_replica_app(
        primary_url=primary_url,
        private_key=private_key,
        chain_id=chain_id,
        platform_pubkey=platform_pubkey,
        write_mode=write_mode,
        sync_interval_ms=sync_interval_ms,
        data_dir=data_dir,
    )
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="octobot-sync-replica", daemon=True)
    thread.start()
    _get_logger().info(
        f"Replica sync server started on http://{host}:{port} "
        f"(primary: {primary_url})"
    )
    return thread
