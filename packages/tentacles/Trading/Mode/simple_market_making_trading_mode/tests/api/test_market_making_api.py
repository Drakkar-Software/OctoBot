#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or modify it under the terms of the GNU
#  General Public License as published by the Free Software Foundation; either version 3.0 of the
#  License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#  even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with OctoBot. If not,
#  see <https://www.gnu.org/licenses/>.

import mock
import pytest
import typing

import octobot_commons.authentication as authentication
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_flow.entities.community.user_authentication as community_user_authentication
import octobot_protocol.models.market_making_configuration as market_making_configuration_model

import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges_core
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.core as market_making_core
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as market_making_models

from tentacles.Trading.Mode.simple_market_making_trading_mode.tests.api.conftest import (
    assert_response_headers,
    dex_exchange_config_dict,
    mocked_common_methods,
)


def _expected_profile_exchange_args(exchange_dicts: list[dict]) -> list[exchanges_core.ExchangeConfig]:
    # Match the same ``ExchangeConfig.model_validate`` the API uses for request bodies; ``url: null`` stays ``None`` when
    # the model uses ``Optional[str]`` (do not force ``url`` to ``""`` here or assertions diverge from runtime).
    return [exchanges_core.ExchangeConfig.model_validate(row) for row in exchange_dicts]


_MARKET_MAKING_ROOT = "/api/v1/tentacles/market-making/"


def _minimal_market_making_config_payload() -> dict:
    return {
        "configuration_type": "market_making",
        "pair_settings": [
            {
                "trading_pair": "BTC/USDT",
                "exchange": "binance",
                "reference_price": [
                    {
                        "exchange": "binance",
                        "pair": "BTC/USDT",
                        "weight": 1,
                        "formula": "",
                    }
                ],
                "min_spread": 0.5,
                "max_spread": 1.0,
                "bids_count": 5,
                "asks_count": 5,
                "orders_distribution": "linear",
                "funds_distribution": "flat",
            }
        ],
    }


@pytest.mark.parametrize("error,status_code", [
    (ValueError("test"), 404),
    (authentication.AuthenticationError("test"), 401),
])
def test_market_making_api_root(client, error: Exception, status_code: int):
    market_making_config = _minimal_market_making_config_payload()
    expected_market_making_configuration = (
        market_making_configuration_model.MarketMakingConfiguration.model_validate(
            market_making_config
        )
    )
    with mocked_common_methods() as get_market_making_profile_data_mock:
        with mock.patch.object(
            market_making_core, "get_market_making_volume", mock.AsyncMock(side_effect=error)
        ) as get_market_making_volume_mock:
            response = client.post(
                _MARKET_MAKING_ROOT,
                json={
                    "type": "market_making_volume",
                    "exchanges": [{"name": "binance", "exchange_type": "spot", "exchange_account_id": "1234567890"}],
                    "config": {"config": market_making_config},
                },
            )
            get_market_making_volume_mock.assert_awaited_once()
            get_market_making_profile_data_mock.assert_called_once()
            get_market_making_profile_data_mock.assert_called_with(
                mock.ANY,
                expected_market_making_configuration,
                user_auth=None,
            )
            assert response.status_code == status_code
            assert "error" in response.json()
            assert str(error) in response.json()["error"]
            assert_response_headers(response)

            get_market_making_volume_mock.reset_mock()
            get_market_making_profile_data_mock.reset_mock()
            response = client.post(
                _MARKET_MAKING_ROOT,
                json={
                    "type": "market_making_volume",
                    "exchanges": [{"name": "binance_futures", "exchange_account_id": "1234567890"}],
                    "config": {"config": market_making_config},
                },
            )
            get_market_making_volume_mock.assert_awaited_once()
            get_market_making_profile_data_mock.assert_called_once()
            get_market_making_profile_data_mock.assert_called_with(
                mock.ANY,
                expected_market_making_configuration,
                user_auth=None,
            )
            assert response.status_code == status_code
            assert "error" in response.json()
            assert str(error) in response.json()["error"]
            assert_response_headers(response)

            get_market_making_volume_mock.reset_mock()
            get_market_making_profile_data_mock.reset_mock()


def test_market_making_dispatch_unknown_traded_pairs_type(client):
    response = client.post(
        _MARKET_MAKING_ROOT,
        json={
            "type": "traded_pairs",
            "exchanges": [{"name": "binance", "exchange_type": "spot"}],
        },
    )
    assert response.status_code == 400
    assert response.json() == "unknown request_type: traded_pairs"
    assert_response_headers(response)


@pytest.mark.parametrize("auth_body,user_auth", [
    (
        {
            "email": "test@example.com",
            "user_id": "1234567890",
            "hidden": True,
        },
        community_user_authentication.UserAuthentication(email="test@example.com", password=None, hidden=True, user_id="1234567890")
    ),
    (None, None)
])
def test_compute_market_making_volume(
    client,
    auth_body: typing.Optional[dict],
    user_auth: typing.Optional[community_user_authentication.UserAuthentication],
):
    with mocked_common_methods() as get_market_making_profile_data_mock:
        with mock.patch.object(
            market_making_core,
            "get_market_making_volume",
            mock.AsyncMock(return_value={"BTC/USDT": 1000.5, "ETH/USDC": 500.25}),
        ) as get_market_making_volume_mock:
            exchange_configs = [{"name": "binance", "exchange_type": "spot", "sandboxed": False, "url": None}]
            market_making_config = _minimal_market_making_config_payload()
            expected_market_making_configuration = (
                market_making_configuration_model.MarketMakingConfiguration.model_validate(
                    market_making_config
                )
            )
            data = {
                "type": "market_making_volume", "exchanges": exchange_configs, "config": {"config": market_making_config}
            }
            if auth_body:
                data["auth"] = auth_body
            response = client.post(
                _MARKET_MAKING_ROOT,
                json=data,
            )
            get_market_making_profile_data_mock.assert_called_once_with(
                _expected_profile_exchange_args(exchange_configs),
                expected_market_making_configuration,
                user_auth=user_auth
            )
            get_market_making_volume_mock.assert_awaited_once()
            assert get_market_making_volume_mock.mock_calls[0].kwargs["user_auth"] == user_auth
            assert response.status_code == 200
            assert response.json() == {"BTC/USDT": 1000.5, "ETH/USDC": 500.25}
            assert_response_headers(response)


def test_compute_market_making_volume_passes_dex_exchange_config(client):
    with mocked_common_methods() as get_market_making_profile_data_mock:
        with mock.patch.object(
            market_making_core,
            "get_market_making_volume",
            mock.AsyncMock(return_value={"BTC/USDT": 1000.5}),
        ) as get_market_making_volume_mock:
            exchange_configs = [dex_exchange_config_dict()]
            market_making_config = _minimal_market_making_config_payload()
            expected_market_making_configuration = (
                market_making_configuration_model.MarketMakingConfiguration.model_validate(
                    market_making_config
                )
            )
            response = client.post(
                _MARKET_MAKING_ROOT,
                json={
                    "type": "market_making_volume",
                    "exchanges": exchange_configs,
                    "config": {"config": market_making_config},
                },
            )

            expected_exchange_configs = _expected_profile_exchange_args(exchange_configs)
            get_market_making_profile_data_mock.assert_called_once_with(
                expected_exchange_configs,
                expected_market_making_configuration,
                user_auth=None,
            )
            parsed_dex_config = expected_exchange_configs[0].dex_config
            assert isinstance(parsed_dex_config, exchanges_core.DEXConfig)
            assert parsed_dex_config.chain_id == "ethereum"
            assert parsed_dex_config.dex_id == "uniswap"
            assert parsed_dex_config.base_token_addresses == ["0xbase"]
            assert parsed_dex_config.quote_token_addresses == ["0xquote"]
            get_market_making_volume_mock.assert_awaited_once()
            assert response.status_code == 200
            assert response.json() == {"BTC/USDT": 1000.5}
            assert_response_headers(response)


@pytest.mark.parametrize("auth_body,user_auth", [
    (
        {
            "email": "test@example.com",
            "user_id": "1234567890",
            "hidden": True,
        },
        community_user_authentication.UserAuthentication(email="test@example.com", password=None, hidden=True, user_id="1234567890")
    ),
    (None, None)
])
def test_get_price_and_predicted_order_book(
    client,
    auth_body: typing.Optional[dict],
    user_auth: typing.Optional[community_user_authentication.UserAuthentication],
):
    with mocked_common_methods() as get_market_making_profile_data_mock:
        expected_result = {
            "BTC/USDT": {
                "price": 50000.0,
                "order_book": {"bids": [[49990, 1.0]], "asks": [[50010, 1.0]]}
            }
        }
        with mock.patch.object(
            market_making_core,
            "get_price_and_predicted_order_book",
            mock.AsyncMock(return_value=expected_result),
        ) as get_price_and_predicted_order_book_mock:
            exchange_configs = [{"name": "binance", "exchange_credential_id": "123-creds", "exchange_type": "spot", "sandboxed": False, "url": None}]
            market_making_config = _minimal_market_making_config_payload()
            expected_market_making_configuration = (
                market_making_configuration_model.MarketMakingConfiguration.model_validate(
                    market_making_config
                )
            )
            response = client.post(
                _MARKET_MAKING_ROOT,
                json={
                    "type": "predicted_order_book", "exchanges": exchange_configs, "config": {"config": market_making_config},
                    "auth": auth_body
                },
            )
            get_market_making_profile_data_mock.assert_called_once_with(
                _expected_profile_exchange_args(exchange_configs),
                expected_market_making_configuration,
                user_auth=user_auth
            )
            get_price_and_predicted_order_book_mock.assert_awaited_once()
            assert get_price_and_predicted_order_book_mock.mock_calls[0].kwargs["user_auth"] == user_auth
            assert response.status_code == 200
            assert response.json() == expected_result
            assert_response_headers(response)


@pytest.mark.parametrize("auth_body,user_auth", [
    (
        {
            "email": "test@example.com",
            "user_id": "1234567890",
            "hidden": True,
        },
        community_user_authentication.UserAuthentication(email="test@example.com", password=None, hidden=True, user_id="1234567890")
    ),
    (None, None)
])
def test_update_liquidity_score(
    client,
    auth_body: typing.Optional[dict],
    user_auth: typing.Optional[community_user_authentication.UserAuthentication],
):
    with mocked_common_methods() as get_market_making_profile_data_mock:
        with mock.patch.object(
            market_making_core, "update_liquidity_scores", mock.AsyncMock(return_value=None)
        ) as update_liquidity_scores_mock:
            with mock.patch.object(
                asyncio_tools,
                "run_background_fingerprint_async_executor",
                return_value=True,
            ) as run_in_executor_mock:
                with mock.patch.dict("os.environ", {
                    "SUPABASE_BUSINESS_USER_EMAIL": "test@example.com",
                    "SUPABASE_BUSINESS_USER_PASSWORD": "test_password"
                }):
                    exchange_configs = [{"name": "binance", "exchange_type": "spot", "sandboxed": True, "url": "123"}]
                    symbols = ["BTC/USDT", "ETH/USDC"]
                    policy = market_making_models.OrderBookFetchPolicy.ALL_SYMBOLS.value
                    response = client.post(
                        _MARKET_MAKING_ROOT,
                        json={
                            "type": "update_liquidity_score",
                            "exchanges": exchange_configs,
                            "symbols": symbols,
                            "policy": policy,
                            "auth": auth_body
                        },
                    )
                    get_market_making_profile_data_mock.assert_called_once_with(
                        _expected_profile_exchange_args(exchange_configs),
                        None,
                        user_auth=user_auth
                    )
                    update_liquidity_scores_mock.assert_called_once()
                    assert update_liquidity_scores_mock.mock_calls[0].args[1] == market_making_models.OrderBookFetchPolicy.ALL_SYMBOLS
                    assert update_liquidity_scores_mock.mock_calls[0].kwargs["user_auth"] == user_auth
                    run_in_executor_mock.assert_called_once()
                    assert response.status_code == 200
                    assert response.json() == "update scheduled"
                    assert_response_headers(response)


@pytest.mark.parametrize("auth_body,user_auth", [
    (
        {
            "email": "test@example.com",
            "user_id": "1234567890",
            "hidden": True,
        },
        community_user_authentication.UserAuthentication(email="test@example.com", password=None, hidden=True, user_id="1234567890")
    ),
    (None, None)
])
def test_update_liquidity_score_already_processing(
    client,
    auth_body: typing.Optional[dict],
    user_auth: typing.Optional[community_user_authentication.UserAuthentication],
):
    with mocked_common_methods() as get_market_making_profile_data_mock:
        with mock.patch.object(
            market_making_core, "update_liquidity_scores", mock.AsyncMock(return_value=None)
        ) as update_liquidity_scores_mock:
            with mock.patch.object(
                asyncio_tools,
                "run_background_fingerprint_async_executor",
                return_value=False,
            ) as run_in_executor_mock:
                with mock.patch.dict("os.environ", {
                    "SUPABASE_BUSINESS_USER_EMAIL": "test@example.com",
                    "SUPABASE_BUSINESS_USER_PASSWORD": "test_password"
                }):
                    exchange_configs = [{"name": "binance", "exchange_type": "spot"}]
                    symbols = ["BTC/USDT"]
                    policy = market_making_models.OrderBookFetchPolicy.GIVEN_SYMBOLS.value
                    response = client.post(
                        _MARKET_MAKING_ROOT,
                        json={
                            "type": "update_liquidity_score",
                            "exchanges": exchange_configs,
                            "symbols": symbols,
                            "policy": policy,
                            "auth": auth_body
                        },
                    )
                    get_market_making_profile_data_mock.assert_called_once_with(
                        _expected_profile_exchange_args(
                            [{**config, "sandboxed": False, "url": None} for config in exchange_configs]
                        ),
                        None,
                        user_auth=user_auth
                    )
                    update_liquidity_scores_mock.assert_called_once()
                    assert update_liquidity_scores_mock.mock_calls[0].args[1] == market_making_models.OrderBookFetchPolicy.GIVEN_SYMBOLS
                    run_in_executor_mock.assert_called_once()
                    assert response.status_code == 200
                    assert response.json() == "update already processing"
                    assert_response_headers(response)
