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
#
#  Duplicated from ``node_api_interface`` tests (same Node API / TestClient needs)
#  so that ``tests.api`` can run under ``tentacles/.../tests`` without ``pytest_plugins``
#  clashing with the node API test tree.

import contextlib
import typing

import mock
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

import octobot_commons.profiles.profile_data as profile_data_import
import octobot_protocol.models.market_making_configuration as market_making_configuration_model

import tentacles.Services.Interfaces.node_api_interface as node_api_interface_module
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.core as market_making_core


def dex_exchange_config_dict(**overrides) -> dict:
    dex_config_overrides = overrides.pop("dex_config", {})
    return {
        "name": "dexscreener",
        "exchange_type": "spot",
        "sandboxed": False,
        "dex_config": {
            "chain_id": "ethereum",
            "dex_id": "uniswap",
            "base_token_addresses": ["0xbase"],
            "quote_token_addresses": ["0xquote"],
            **dex_config_overrides,
        },
        **overrides,
    }


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


def get_all_routes(fastapi_app: FastAPI) -> list[str]:
    route_paths: list[str] = []
    for route in fastapi_app.routes:
        if (
            isinstance(route, APIRoute)
            and "{" not in route.path
            and route.path.startswith("/api/v1")
        ):
            route_paths.append(route.path)
    return sorted(set(route_paths))


@contextlib.contextmanager
def mocked_common_methods():
    async def _profile_data_factory(
        exchange_configs: list,
        market_making_config: typing.Optional[market_making_configuration_model.MarketMakingConfiguration],
        user_auth=None,
        **_kwargs,
    ):
        profile_data = profile_data_import.ProfileData(
            profile_data_import.ProfileDetailsData(),
            [],
            profile_data_import.TradingData("")
        )
        return profile_data

    with mock.patch.object(
        market_making_core,
        "get_market_making_profile_data",
        mock.AsyncMock(side_effect=_profile_data_factory),
    ) as get_market_making_profile_data_mock:
        yield get_market_making_profile_data_mock


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
