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

import mimetypes
import pathlib

import fastapi
import fastapi.responses as fastapi_responses

try:
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.store as store_module
except ImportError:
    import mobile_ui.constants as constants  # type: ignore[no-redef]
    import mobile_ui.store as store_module  # type: ignore[no-redef]


def _content_type_for_path(path: pathlib.Path) -> str:
    extension = path.suffix.lower()
    if extension in constants.CONTENT_TYPE_BY_EXTENSION:
        return constants.CONTENT_TYPE_BY_EXTENSION[extension]
    guessed, _encoding = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "application/octet-stream"


def _cache_control_for_path(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    for prefix in constants.CACHE_IMMUTABLE_PREFIXES:
        if normalized.startswith(prefix):
            return constants.CACHE_CONTROL_IMMUTABLE
    return constants.CACHE_CONTROL_NO_CACHE


def _is_unsafe_request_path(path: str) -> bool:
    if not path:
        return False
    if chr(92) in path:
        return True
    if any(ord(character) == 0 for character in path):
        return True
    segments = path.replace("\\", "/").split("/")
    return ".." in segments


def _should_spa_fallback(relative_path: str) -> bool:
    if relative_path.startswith("_expo/") or relative_path.startswith("assets/"):
        return False
    last_segment = relative_path.rsplit("/", 1)[-1]
    return "." not in last_segment


def _serve_mobile_path(
    request: fastapi.Request,
    path: str,
) -> fastapi_responses.Response:
    mobile_store: store_module.MobileUiStore = request.app.state.mobile_ui_store
    active_dir = mobile_store.active_directory()
    if active_dir is None:
        return fastapi_responses.HTMLResponse(
            content=constants.NOT_INSTALLED_HTML,
            status_code=503,
            headers={"Cache-Control": constants.CACHE_CONTROL_NO_CACHE},
        )

    if _is_unsafe_request_path(path):
        raise fastapi.HTTPException(status_code=404)

    candidate = (active_dir / path).resolve()
    if not candidate.is_relative_to(active_dir.resolve()):
        raise fastapi.HTTPException(status_code=404)

    if candidate.is_file():
        relative_file = path.replace("\\", "/")
        headers = {"Cache-Control": _cache_control_for_path(relative_file)}
        return fastapi_responses.FileResponse(
            path=candidate,
            media_type=_content_type_for_path(candidate),
            headers=headers,
        )

    if _should_spa_fallback(path.replace("\\", "/")):
        index_path = active_dir / "index.html"
        if index_path.is_file():
            return fastapi_responses.FileResponse(
                path=index_path,
                media_type=_content_type_for_path(index_path),
                headers={"Cache-Control": constants.CACHE_CONTROL_NO_CACHE},
            )

    raise fastapi.HTTPException(status_code=404)


def add_mobile_ui_routes(app: fastapi.FastAPI) -> None:
    @app.get("/mobile", include_in_schema=False)
    async def serve_mobile_root(request: fastapi.Request) -> fastapi_responses.Response:
        return _serve_mobile_path(request, "index.html")

    @app.get("/mobile/", include_in_schema=False)
    async def serve_mobile_root_slash(request: fastapi.Request) -> fastapi_responses.Response:
        return _serve_mobile_path(request, "index.html")

    @app.get("/mobile/{path:path}", include_in_schema=False)
    async def serve_mobile_file(
        request: fastapi.Request,
        path: str,
    ) -> fastapi_responses.Response:
        return _serve_mobile_path(request, path)
