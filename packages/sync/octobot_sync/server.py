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
from satellite_server.storage.s3 import S3ObjectStore, S3StorageOptions

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


def _build_app(platform_pubkey: str | None = None) -> tuple:
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

    registry = chain.ChainRegistry()

    evm_base_rpc = os.getenv("EVM_BASE_RPC")
    evm_contract_base = os.getenv("EVM_CONTRACT_BASE")
    if evm_base_rpc and evm_contract_base:
        registry.register(chain.EvmChain("evm:8453", evm_base_rpc, evm_contract_base))
    else:
        registry.register(chain.EvmChain("evm:8453"))

    if platform_pubkey:
        os.environ.setdefault("PLATFORM_PUBKEY_EVM", platform_pubkey)

    app = sync_app.create_app(nonce, object_store, registry)
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
