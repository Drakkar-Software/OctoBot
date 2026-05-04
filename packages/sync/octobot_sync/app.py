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
from collections.abc import Callable

from fastapi import FastAPI
from starfish_server.storage.base import AbstractObjectStore
from starfish_server.router.route_builder import create_sync_router, SyncRouterOptions
from starfish_server.config.schema import ConfigEndpointOptions, SyncConfig

import octobot_sync.auth as auth
import octobot_sync.constants as constants
import octobot_sync.sync as sync


class NamespaceRewriteMiddleware:
    """Rewrite /<ns>/<ver>/<rest> -> /<ver>/<ns>/<rest>. Mimics the nginx
    rewrite used in production so signed canonicals match server routes."""

    def __init__(self, app, namespaces: list[str]):
        self.app = app
        self.namespaces = list(namespaces)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            root_path = scope.get("root_path", "")
            # Starlette sets root_path to the mount prefix but leaves path unchanged;
            # effective_path is what Starlette routes against (path minus root_path).
            if root_path and path.startswith(root_path) and (len(path) == len(root_path) or path[len(root_path)] == "/"):
                effective = path[len(root_path):] or "/"
            else:
                effective = path
            ver = constants.STARFISH_SERVER_MAJOR_VERSION
            for ns in self.namespaces:
                prefix = f"/{ns}/{ver}"
                if effective == prefix or effective.startswith(prefix + "/"):
                    rest = effective[len(prefix):]
                    new_effective = f"/{ver}/{ns}{rest}"
                    new_path = root_path + new_effective
                    scope = dict(scope)
                    scope["path"] = new_path
                    if scope.get("raw_path") is not None:
                        scope["raw_path"] = new_path.encode("ascii")
                    break
        await self.app(scope, receive, send)


def create_app(
    nonce: auth.NonceStore,
    object_store: AbstractObjectStore,
    collections_path: str | None = None,
    is_allowed: Callable[[str], bool] | None = None,
    encryption_secret: str | None = None,
    sync_config: SyncConfig | None = None,
):
    if encryption_secret is None:
        encryption_secret = os.environ.get("ENCRYPTION_SECRET")

    if sync_config is None:
        sync_config = sync.load_sync_config(collections_path)

    app = FastAPI(title="OctoBot Sync — Signal Sync Server")

    sync_router = create_sync_router(
        SyncRouterOptions(
            store=object_store,
            config=sync_config,
            role_resolver=sync.create_role_resolver(nonce, is_allowed=is_allowed),
            encryption_secret=encryption_secret,
            identity_encryption_info=constants.HKDF_INFO_USER_DATA,
            config_endpoint=ConfigEndpointOptions(auth="public"),
        )
    )
    app.include_router(sync_router, prefix=f"/{constants.STARFISH_SERVER_MAJOR_VERSION}")

    @app.get("/health")
    async def health():
        return {"ok": True}

    namespaces = list((sync_config.namespaces or {}).keys())
    if namespaces:
        return NamespaceRewriteMiddleware(app, namespaces=namespaces)
    return app
