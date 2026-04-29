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

import typing

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware


import tentacles.Services.Interfaces.node_api_interface as node_api_interface_module


@pytest.fixture()
def app() -> FastAPI:
    fastapi_app = node_api_interface_module.NodeApiInterface.create_app()
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return fastapi_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def assert_response_headers(
    response,
    expected_content_type: typing.Optional[str] = None,
    expected_content_length: typing.Optional[int] = None,
):
    headers = {header_key.lower(): header_value for header_key, header_value in response.headers.items()}
    if expected_content_type is not None:
        assert headers["content-type"] == expected_content_type, (
            f"Content-Type is {headers.get('content-type')}"
        )
    else:
        assert headers["content-type"] == "application/json", (
            f"Content-Type is {headers.get('content-type')}"
        )
    # Starlette CORSMiddleware only sets this when the request is a CORS request (e.g. Origin set);
    # plain TestClient POST without Origin may omit the header.
    allow_origin = headers.get("access-control-allow-origin")
    if allow_origin is not None:
        assert allow_origin == "*", (
            f"Access-Control-Allow-Origin is {allow_origin}"
        )
    if expected_content_length is not None:
        assert int(headers["content-length"]) == expected_content_length, (
            f"Content-Length is {headers.get('content-length')}"
        )
    else:
        assert int(headers.get("content-length", 0)) > 0, (
            f"Content-Length is {headers.get('content-length')}"
        )
