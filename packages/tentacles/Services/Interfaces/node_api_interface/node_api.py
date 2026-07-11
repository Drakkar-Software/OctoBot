#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

import octobot.community.authentication as community_auth
import octobot_services.constants as services_constants
import octobot_services.interfaces as services_interfaces
import octobot_services.interfaces.util.web as web_util
import octobot_commons.logging as octobot_commons_logging
import octobot_node.config as node_config
import octobot_node.scheduler as scheduler # noqa: F401
import octobot_sync.server as sync_server


# Service_bases is only needed at runtime, not for build
try:
    import tentacles.Services.Services_bases as Service_bases
    import tentacles.Services.Services_bases.node_api_service.node_api as node_api_service
except ImportError:
    Service_bases = None
    node_api_service = None

try:
    from tentacles.Services.Interfaces.node_api_interface.utils import get_dist_directory
    from tentacles.Services.Interfaces.node_api_interface.api.main import build_api_router
except ImportError:
    from utils import get_dist_directory  # type: ignore[no-redef]
    import api.main as _api_main  # type: ignore[no-redef]
    build_api_router = _api_main.build_api_router

LOCALHOST_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
OCTOBOT_CLOUD_ORIGIN_REGEX = r"^https://([a-z0-9-]+\.)*octobot\.cloud$"
ALLOWED_ORIGIN_REGEX = f"({LOCALHOST_ORIGIN_REGEX}|{OCTOBOT_CLOUD_ORIGIN_REGEX})"


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    # Fallback for routes without tags (e.g., SPA root)
    return route.name or route.path.replace("/", "-").strip("-")


class NodeApiInterface(services_interfaces.AbstractInterface):
    API_NAME = "OctoBot Node API"

    try:
        REQUIRED_SERVICES = [Service_bases.NodeApiService]
    except AttributeError:
        # fallback to empty array (build time)
        REQUIRED_SERVICES = []
    
    def __init__(self, config):
        super().__init__(config)
        self.logger = self.get_logger()
        self.server = None
        self.app = None
        self.host = None
        self.port = None
        self.node_api_service = None
        self._serve_finished: threading.Event | None = None

    async def _inner_start(self) -> bool:
        return self.threaded_start()

    async def _async_run(self) -> bool:
        if self.node_api_service is None:
            self.node_api_service = Service_bases.NodeApiService.instance()
        self.host = self.node_api_service.get_bind_host()
        self.port = self.node_api_service.get_bind_port()
        node_sqlite_file = self.node_api_service.get_node_sqlite_file()
        node_postgres_url = self.node_api_service.get_node_postgres_url()
        if node_sqlite_file:
            node_config.settings.SCHEDULER_SQLITE_FILE = node_sqlite_file
        if node_postgres_url is not None:
            node_config.settings.SCHEDULER_POSTGRES_URL = node_postgres_url
        if not scheduler.is_initialized():
            self.logger.warning(
                "Scheduler not initialized by NodeApiService.prepare(); initializing now"
            )
            scheduler.initialize_scheduler()
        host = self.host
        port = self.port
        self.app = self.create_app()
        # Set CORS from service config
        cors_origins_str = self.node_api_service.get_backend_cors_origins()
        cors_origins = [i.strip() for i in cors_origins_str.split(",") if i.strip()] if cors_origins_str else []
        extra_regex = self.node_api_service.get_backend_cors_origin_regex()
        origin_regex = f"({ALLOWED_ORIGIN_REGEX}|{extra_regex})" if extra_regex else ALLOWED_ORIGIN_REGEX
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_origin_regex=origin_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        self.server = uvicorn.Server(config)
        self._serve_finished = threading.Event()
        dist_dir = get_dist_directory()
        if dist_dir and self._should_open_node_ui_in_browser():
            self._open_node_ui_on_browser()
        try:
            await self.server.serve()
        finally:
            if self._serve_finished is not None:
                self._serve_finished.set()
        return True

    async def stop(self):
        if self.server is not None:
            self.server.should_exit = True

    def _should_open_node_ui_in_browser(self) -> bool:
        try:
            return self.config[services_constants.CONFIG_CATEGORY_SERVICES] \
                [services_constants.CONFIG_NODE_API][services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER]
        except KeyError:
            return True

    def _open_node_ui_on_browser(self):
        try:
            web_util.open_in_background_browser(
                f"http://{node_api_service.LOCAL_HOST_IP}:{self.port}/app"
            )
        except Exception as err:
            self.logger.warning(
                f"Impossible to open automatically node web interface: {err} ({err.__class__.__name__})"
            )

    @classmethod
    def create_app(cls) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            # Shutdown: trading signal channel first, then DBOS
            await scheduler.shutdown_scheduler_and_trading_signal_channel()

        app = FastAPI(
            title=cls.API_NAME,
            openapi_url="/api/v1/openapi.json",
            generate_unique_id_function=custom_generate_unique_id,
            lifespan=lifespan,
        )

        octobot_commons_logging.register_unhandled_exception_handler(app, "node_api_interface")

        app.include_router(build_api_router(), prefix="/api/v1")

        sync_server.set_data_callbacks(sync_server.get_data, sync_server.put_data)
        app.mount(
            "/sync",
            sync_server.build_default_sync_app(
                # Service-level allowlist: only the node's own wallets may use the
                # sync server. Under cap-certs the request identity is the Starfish
                # user_id, so derive each local wallet's user_id with the same
                # bootstrap challenge the client uses (cap scoping then confines
                # each caller to its own users/{user_id}/* paths).
                is_allowed_user_id=lambda user_id: any(
                    sync_server.derive_user_id(w.private_key) == user_id
                    for w in community_auth.CommunityAuthentication.instance().list_wallet_entries()
                ),
            ),
        )

        # Get the path to the dist folder (works for both development and installed packages)
        dist_dir = get_dist_directory()

        # Serve static files from the dist folder only if UI is enabled
        if dist_dir:
            assets_dir = dist_dir / "assets"
            if assets_dir.exists():
                # Mount assets under /app/assets to match the SPA base path
                app.mount("/app/assets", StaticFiles(directory=str(assets_dir)), name="assets")

            # Serve SPA root for /app
            @app.get("/app")
            async def serve_spa_app_root():
                index_path = dist_dir / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                raise HTTPException(status_code=404, detail="Frontend build not found")

            # Serve SPA for /app routes
            @app.get("/app/{path:path}")
            async def serve_spa_app(request: Request, path: str):
                # Don't interfere with assets (already handled by mount)
                if path.startswith("assets/"):
                    raise HTTPException(status_code=404)

                # Serve index.html for all /app routes (SPA routing)
                index_path = dist_dir / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                raise HTTPException(status_code=404, detail="Frontend build not found")

        return app
