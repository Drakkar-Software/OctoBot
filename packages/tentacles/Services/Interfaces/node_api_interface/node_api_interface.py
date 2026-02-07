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
from contextlib import asynccontextmanager

import sentry_sdk
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

import octobot_services.constants as services_constants
import octobot_services.interfaces as services_interfaces
import tentacles.Services.Services_bases as Service_bases
from octobot_node import PROJECT_NAME
from tentacles.Services.Interfaces.node_api_interface.api.main import build_api_router
from octobot_node.config import settings
from tentacles.Services.Interfaces.node_api_interface.utils import get_dist_directory


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    # Fallback for routes without tags (e.g., SPA root)
    return route.name or route.path.replace("/", "-").strip("-")


class NodeApiInterface(services_interfaces.AbstractInterface):
    REQUIRED_SERVICES = [Service_bases.NodeApiService]

    def __init__(self, config):
        super().__init__(config)
        self.logger = self.get_logger()
        self.server = None
        self.app = None
        self.host = None
        self.port = None
        self.node_api_service = None

    async def _inner_start(self) -> bool:
        return self.threaded_start()

    async def _async_run(self) -> bool:
        if self.node_api_service is None:
            self.node_api_service = Service_bases.NodeApiService.instance()
        self.host = self.node_api_service.get_bind_host()
        self.port = self.node_api_service.get_bind_port()
        admin_username = self.node_api_service.get_admin_username()
        admin_password = self.node_api_service.get_admin_password()
        node_sqlite_file = self.node_api_service.get_node_sqlite_file()
        node_redis_url = self.node_api_service.get_node_redis_url()
        if admin_username:
            settings.ADMIN_USERNAME = admin_username
        if admin_password:
            settings.ADMIN_PASSWORD = admin_password
        if node_sqlite_file:
            settings.SCHEDULER_SQLITE_FILE = node_sqlite_file
        if node_redis_url is not None:
            settings.SCHEDULER_REDIS_URL = node_redis_url
        host = self.host
        port = self.port
        self.app = self.create_app()
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        self.server = uvicorn.Server(config)
        await self.server.serve()
        return True

    async def stop(self):
        if self.server is not None:
            self.server.should_exit = True

    @classmethod
    def create_app(cls) -> FastAPI:
        if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
            sentry_sdk.init(
                dsn=str(settings.SENTRY_DSN),
                enable_tracing=True,
                include_local_variables=False,   # careful not to upload sensitive data
            )

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage application lifespan: startup and shutdown events."""
            # Startup - scheduler starts automatically on import
            # Import scheduler module to ensure it's initialized
            from octobot_node.scheduler import scheduler  # noqa: F401
            from octobot_node.scheduler import SCHEDULER, CONSUMER
            yield
            # Shutdown
            SCHEDULER.stop()
            CONSUMER.stop()

        app = FastAPI(
            title=PROJECT_NAME,
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            generate_unique_id_function=custom_generate_unique_id,
            lifespan=lifespan,
        )

        # Set all CORS enabled origins
        if settings.all_cors_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=settings.all_cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        app.include_router(build_api_router(), prefix=settings.API_V1_STR)

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
                """
                Serve the React app for /app routes.
                This enables client-side routing.
                """
                # Don't interfere with assets (already handled by mount)
                if path.startswith("assets/"):
                    raise HTTPException(status_code=404)

                # Serve index.html for all /app routes (SPA routing)
                index_path = dist_dir / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path))
                raise HTTPException(status_code=404, detail="Frontend build not found")

        return app
