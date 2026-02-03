#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from octobot_node import PROJECT_NAME
from octobot_node.app.api.main import api_router
from octobot_node.app.core.config import settings
from octobot_node.app.utils import get_dist_directory
from octobot_node.scheduler import SCHEDULER, CONSUMER


def custom_generate_unique_id(route: APIRoute) -> str:
    if route.tags:
        return f"{route.tags[0]}-{route.name}"
    # Fallback for routes without tags (e.g., SPA root)
    return route.name or route.path.replace("/", "-").strip("-")


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

app.include_router(api_router, prefix=settings.API_V1_STR)

# Get the path to the dist folder (works for both development and installed packages)
DIST_DIR = get_dist_directory()

# Serve static files from the dist folder only if UI is enabled
if DIST_DIR:
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        # Mount assets under /app/assets to match the SPA base path
        app.mount("/app/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Serve SPA root for /app
    @app.get("/app")
    async def serve_spa_app_root():
        index_path = DIST_DIR / "index.html"
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
        index_path = DIST_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend build not found")
