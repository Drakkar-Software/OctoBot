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

from collections.abc import Callable

from fastapi import FastAPI
from starfish_server.storage.base import AbstractObjectStore
from starfish_server.router.route_builder import create_sync_router, SyncRouterOptions
from starfish_server.config.schema import ConfigEndpointOptions, SyncConfig
from starfish_protocol.plugins import ServerPlugin
from starfish_server.router.cap_resolver import create_cap_cert_role_resolver, CapAuthError
from starfish_server.auth.nonce_cache import create_in_memory_nonce_cache
from starfish_server.auth.revocation_store import create_in_memory_revocation_store

import starfish_identities

import octobot_commons.logging as octobot_commons_logging
import octobot_sync.constants as constants
import octobot_sync.sync as sync


_VERSION_MARKER = f"/{constants.STARFISH_SERVER_MAJOR_VERSION}/"


class SignedPathMiddleware:
    """Normalize the inbound path to the cap-signed form (``/v1/...``).

    The Starfish cap resolver verifies each request signature against
    ``request.url.path``. The client signs the bare ``/v1/{namespace}/...`` path
    (it has no knowledge of where the server mounts the app), so any prefix the
    server adds — a Starlette ``/sync`` mount in-process, an nginx ``location`` in
    production — must be stripped before the resolver sees the path, or every
    signature mismatches. We slice from the leading ``/v1/`` segment and clear
    ``root_path`` so ``request.url.path`` equals exactly what the client signed,
    independent of how the app is mounted. (Replaces the v2
    ``NamespaceRewriteMiddleware``, which rewrote the old ``/{ns}/v1`` shape.)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            full = (scope.get("root_path", "") or "") + scope.get("path", "")
            idx = full.find(_VERSION_MARKER)
            if idx != -1:
                new_path = full[idx:]
                scope = dict(scope)
                scope["path"] = new_path
                scope["root_path"] = ""
                if scope.get("raw_path") is not None:
                    scope["raw_path"] = new_path.encode("latin-1")
        await self.app(scope, receive, send)


def _build_role_resolver(is_allowed_user_id: Callable[[str], bool] | None):
    """Cap-cert role resolver (device caps), optionally gated by a userId allowlist.

    The allowlist is a coarse, service-level gate: cap scoping already confines
    each caller to its own ``users/{user_id}/*`` paths, so this only decides who
    may use the server at all. Allowed userIds are derived from the node's own
    wallet keys (see ``node_api``), keyed on the same identity the cap resolver
    binds (``AuthResult.identity`` == the device cap's ``issUserId``).
    """
    resolver = create_cap_cert_role_resolver(
        nonce_cache=create_in_memory_nonce_cache(),
        revocation_store=create_in_memory_revocation_store(),
        plugins=[starfish_identities.identities_server_plugin],
        allow_anonymous=False,
        # Pre-auth body ceiling, enforced BEFORE the per-collection maxBodyBytes.
        # Defaults to 64KB, which would 413 large private documents; raise it to
        # the largest collection limit so per-collection maxBodyBytes governs.
        max_body_bytes=constants.MAX_BODY_SIZE_PRIVATE,
    )
    if is_allowed_user_id is None:
        return resolver

    async def gated_resolver(request):
        result = await resolver(request)
        if result.identity and not is_allowed_user_id(result.identity):
            raise CapAuthError(403, "user not allowed")
        return result

    return gated_resolver


def create_app(
    object_store: AbstractObjectStore,
    collections_path: str | None = None,
    is_allowed_user_id: Callable[[str], bool] | None = None,
    sync_config: SyncConfig | None = None,
    plugins: list[ServerPlugin] | None = None,
):
    if sync_config is None:
        sync_config = sync.load_sync_config(collections_path)

    app = FastAPI(title="OctoBot Sync — Signal Sync Server")

    octobot_commons_logging.register_unhandled_exception_handler(app, "OctoBot-Sync")

    sync_router = create_sync_router(
        SyncRouterOptions(
            store=object_store,
            config=sync_config,
            role_resolver=_build_role_resolver(is_allowed_user_id),
            config_endpoint=ConfigEndpointOptions(auth="public"),
            plugins=plugins,
        )
    )
    app.include_router(sync_router, prefix=f"/{constants.STARFISH_SERVER_MAJOR_VERSION}")

    @app.get("/health")
    async def health():
        return {"ok": True}

    # Always wrap: the cap resolver verifies the request signature against
    # request.url.path, which must equal the client-signed /v1/... path
    # regardless of how this app is mounted (see SignedPathMiddleware).
    return SignedPathMiddleware(app)
