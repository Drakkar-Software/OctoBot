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

"""Application factory — creates the FastAPI app with all routes."""

import os

from fastapi import FastAPI
from satellite_server.interfaces import IObjectStore
from satellite_server.router.route_builder import create_sync_router, SyncRouterOptions

import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import octobot_sync.routes as routes
import octobot_sync.sync as sync


def create_app(
    nonce: auth.NonceStore,
    object_store: IObjectStore,
    registry: chain.ChainRegistry,
    collections_path: str | None = None,
) -> FastAPI:
    app = FastAPI(title="OctoBot Sync — Signal Sync Server")

    platform_pubkey = os.environ["PLATFORM_PUBKEY_EVM"]
    encryption_secret = os.environ["ENCRYPTION_SECRET"]
    platform_encryption_secret = os.environ["PLATFORM_ENCRYPTION_SECRET"]

    # Store shared deps on app.state for route handlers
    app.state.object_store = object_store
    app.state.nonce = nonce
    app.state.registry = registry
    app.state.platform_pubkey = platform_pubkey
    app.state.encryption_secret = encryption_secret
    app.state.platform_encryption_secret = platform_encryption_secret

    sync_config = sync.load_sync_config(collections_path)

    # Health + verify (unversioned)
    app.include_router(routes.health.router)
    app.include_router(routes.verify.router)

    # Satellite sync router (handles all sync collections)
    sync_router = create_sync_router(
        SyncRouterOptions(
            store=object_store,
            config=sync_config,
            role_resolver=sync.create_role_resolver(registry, nonce, platform_pubkey),
            role_enricher=sync.create_role_enricher(registry),
            encryption_secret=encryption_secret,
            identity_encryption_info=constants.HKDF_INFO_USER_DATA,
            server_encryption_secret=platform_encryption_secret,
            server_identity=platform_pubkey,
            server_encryption_info=constants.HKDF_INFO_PLATFORM_DATA,
            signature_verifier=sync.create_signature_verifier(registry),
        )
    )
    app.include_router(sync_router, prefix="/v1")

    # Manual routes (non-sync)
    app.include_router(routes.product_meta.router, prefix="/v1")
    app.include_router(routes.product.router, prefix="/v1")

    return app
