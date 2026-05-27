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

import os
import mock
import typing

import octobot_commons.symbols.symbol_util as commons_symbols
import octobot_protocol.models as protocol_models
import tentacles.Services.Interfaces.node_api_interface.core.exchanges as node_exchanges_core

from tentacles.Services.Interfaces.node_api_interface.tests.conftest import assert_response_headers


_TRADED_PAIRS = "/api/v1/exchanges/traded-pairs"
_TRADED_PAIRS_AND_TIMEFRAMES = "/api/v1/exchanges/traded-pairs-and-timeframes"


def _is_github_actions() -> bool:
    return bool(os.getenv("GITHUB_ACTIONS"))


# binanceus works on GitHub CI; binance is used for local runs.
def _remote_exchange_display_name() -> str:
    return "binanceus" if _is_github_actions() else "binance"


def _query_params_for_spot_exchange() -> dict[str, typing.Any]:
    exchange_name = _remote_exchange_display_name()
    return {
        "id": "test-exchange-config",
        "name": f"{exchange_name}-test",
        "exchange": exchange_name,
        "sandboxed": False,
        "trading_type": protocol_models.TradingType.SPOT.value,
    }


def _mock_pairs_timeframes_payload() -> dict[str, dict[str, list[str]]]:
    pair_key = node_exchanges_core.ExchangeInfo.PAIRS.value
    timeframe_key = node_exchanges_core.ExchangeInfo.TIMEFRAMES.value
    return {
        "binance": {
            pair_key: ["BTC/USDT", "ETH/USDC"],
            timeframe_key: ["1h", "4h"],
        }
    }


class TestExchangesGetTradedPairs:
    def test_returns_pairs_map_only(
        self,
        client: typing.Any,
    ) -> None:
        raw = _mock_pairs_timeframes_payload()
        with mock.patch.object(
            node_exchanges_core,
            "get_traded_pairs_and_timeframes_by_exchange",
            mock.AsyncMock(return_value=raw),
        ) as get_pairs_tf_mock:
            response = client.get(
                _TRADED_PAIRS,
                params={
                    "id": "test-exchange-config",
                    "name": "binance-test",
                    "exchange": "binance",
                    "sandboxed": False,
                    "trading_type": "spot",
                },
            )
            get_pairs_tf_mock.assert_awaited_once()
            assert response.status_code == 200
            pair_key = node_exchanges_core.ExchangeInfo.PAIRS.value
            assert response.json() == {
                "binance": raw["binance"][pair_key],
            }
            assert_response_headers(response)


class TestExchangesGetTradedPairsAndTimeframes:
    def test_returns_full_payload_from_core(
        self,
        client: typing.Any,
    ) -> None:
        expected = _mock_pairs_timeframes_payload()
        with mock.patch.object(
            node_exchanges_core,
            "get_traded_pairs_and_timeframes_by_exchange",
            mock.AsyncMock(return_value=expected),
        ) as get_pairs_tf_mock:
            response = client.get(
                _TRADED_PAIRS_AND_TIMEFRAMES,
                params={
                    "id": "test-exchange-config",
                    "name": "binance-test",
                    "exchange": "binance",
                    "sandboxed": False,
                    "trading_type": "spot",
                },
            )
            get_pairs_tf_mock.assert_awaited_once()
            assert response.status_code == 200
            assert response.json() == expected
            assert_response_headers(response)


class TestExchangesTradedPairsIntegration:
    def test_includes_btc_usdt_on_public_exchange(
        self,
        client: typing.Any,
    ) -> None:
        display_name = _remote_exchange_display_name()
        response = client.get(
            _TRADED_PAIRS_AND_TIMEFRAMES,
            params=_query_params_for_spot_exchange(),
        )
        assert response.status_code == 200
        body: dict = response.json()
        assert display_name in body
        pair_key = node_exchanges_core.ExchangeInfo.PAIRS.value
        assert pair_key in body[display_name]
        pairs_list: list = body[display_name][pair_key]
        assert isinstance(pairs_list, list)
        assert len(pairs_list) > 0
        assert "BTC/USDT" in pairs_list
        for traded_symbol in pairs_list:
            assert commons_symbols.parse_symbol(traded_symbol).is_spot(), (
                f"with default spot exchange type, only spot pairs are returned; got {traded_symbol!r}"
            )
        assert_response_headers(response)
