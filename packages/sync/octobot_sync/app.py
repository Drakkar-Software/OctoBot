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

import httpx
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response
from starfish_server.storage.base import AbstractObjectStore
from starfish_server.router.route_builder import create_sync_router, SyncRouterOptions
from starfish_server.replica import ReplicaManager, create_replica_router

import octobot_sync.auth as auth
import octobot_sync.chain as chain
import octobot_sync.constants as constants
import octobot_sync.routes as routes
import octobot_sync.sync as sync


def create_app(
    nonce: auth.NonceStore,
    object_store: AbstractObjectStore,
    registry: chain.ChainRegistry,
    collections_path: str | None = None,
    primary_url: str | None = None,
    auth_provider: auth.StarfishAuthProvider | None = None,
    write_mode: str = "bidirectional",
    sync_interval_ms: int = 60_000,
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

    replica_manager = None
    if primary_url:
        # Replica mode: split collections into replicable vs proxied
        sync_config, proxied_collections = sync.make_replica_config(
            sync_config, primary_url, write_mode, sync_interval_ms,
        )

        # Create authenticated httpx client for replica-to-primary requests
        replica_client = _create_authenticated_client(auth_provider)
        replica_manager = ReplicaManager(
            store=object_store,
            collections=sync_config.collections,
            client=replica_client,
        )

        # Proxy routes for per-user/templated collections
        if proxied_collections:
            proxy_router = _create_proxy_router(primary_url, replica_client)
            app.include_router(proxy_router, prefix="/v1")

        # Replica notification endpoint
        replica_router = create_replica_router(
            replica_manager=replica_manager,
            collections=sync_config.collections,
        )
        app.include_router(replica_router)

    # Starfish sync router (handles all sync collections)
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
            replica_manager=replica_manager,
        )
    )
    app.include_router(sync_router, prefix="/v1")

    # Manual routes (non-sync)
    app.include_router(routes.product_meta.router, prefix="/v1")
    app.include_router(routes.product.router, prefix="/v1")

    if replica_manager:
        @app.on_event("startup")
        async def _start_replica():
            await replica_manager.start()

        @app.on_event("shutdown")
        async def _stop_replica():
            await replica_manager.stop()

    return app


def _create_authenticated_client(
    auth_provider: auth.StarfishAuthProvider | None,
) -> httpx.AsyncClient:
    """Create an httpx client that signs requests using the StarfishAuthProvider."""
    if auth_provider is None:
        return httpx.AsyncClient(timeout=30.0)

    async def _auth_hook(request: httpx.Request):
        body_str = request.content.decode("utf-8") if request.content else None
        headers = await auth_provider(
            method=request.method,
            path=str(request.url.raw_path, "ascii"),
            body=body_str,
        )
        request.headers.update(headers)

    return httpx.AsyncClient(
        timeout=30.0,
        event_hooks={"request": [_auth_hook]},
    )


def _create_proxy_router(primary_url: str, client: httpx.AsyncClient) -> APIRouter:
    """Create a catch-all router that proxies requests to the primary server."""
    router = APIRouter()

    @router.api_route(
        "/{action:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    )
    async def _proxy(request: Request, action: str):
        target_url = f"{primary_url.rstrip('/')}/{action}"
        body = await request.body()

        # Forward headers (except host)
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length")
        }

        resp = await client.request(
            method=request.method,
            url=target_url,
            content=body if body else None,
            headers=headers,
            params=dict(request.query_params),
        )

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )

    return router
