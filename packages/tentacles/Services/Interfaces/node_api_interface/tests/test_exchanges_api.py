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

import octobot_commons
import octobot_commons.symbols.symbol_util as commons_symbols
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import tentacles.Services.Interfaces.node_api_interface.core.exchanges as node_exchanges_core

from tentacles.Services.Interfaces.node_api_interface.tests.conftest import assert_response_headers


_TRADED_PAIRS = "/api/v1/exchanges/traded-pairs"
_TRADED_PAIRS_AND_TIMEFRAMES = "/api/v1/exchanges/traded-pairs-and-timeframes"
_DEX_PAIRS = "/api/v1/exchanges/dex_pairs"
DEX_BTCB_USDT = "BTCB/USDT"
BTCB_BSC_TOKEN_ADDRESS = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
USDT_BSC_TOKEN_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"
DEX_BTCB_USDT_ADDRESS_PAIR = f"{BTCB_BSC_TOKEN_ADDRESS}/{USDT_BSC_TOKEN_ADDRESS}"
BEP20_NETWORK = "BEP20"
UNISWAP_DEX = "UNISWAP"
DEX_BTCB_USDT_ANY_BEP20_DEX = (
    f"{DEX_BTCB_USDT}{octobot_commons.NETWORK_SEPARATOR}{BEP20_NETWORK}"
    f"{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"
)
DEX_BTCB_USDT_BEP20_UNISWAP = (
    f"{DEX_BTCB_USDT}{octobot_commons.NETWORK_SEPARATOR}{BEP20_NETWORK}"
    f"{octobot_commons.DEX_SEPARATOR}{UNISWAP_DEX}"
)
DEX_BTCB_USDT_ADDRESS_ANY_BEP20_DEX = (
    f"{DEX_BTCB_USDT_ADDRESS_PAIR}{octobot_commons.NETWORK_SEPARATOR}{BEP20_NETWORK}"
    f"{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"
)
DEX_BTCB_USDT_ADDRESS_BEP20 = (
    f"{DEX_BTCB_USDT_ADDRESS_PAIR}{octobot_commons.NETWORK_SEPARATOR}{BEP20_NETWORK}"
)


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


def _mock_dex_pairs_payload() -> dict[str, list[dict]]:
    return {
        "BTCB/USDT": [
            {
                "symbol": "BTCB/USDT",
                "network": "BEP20",
                "dex": "PANCAKESWAP",
                "baseTokenAddress": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
                "quoteTokenAddress": "0x55d398326f99059fF775485246999027B3197955",
                "price": 73448.58,
                "quoteLiquidity": 52.37,
            },
            {
                "symbol": "BTCB/USDT",
                "network": "BEP20",
                "dex": "UNISWAP",
                "baseTokenAddress": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
                "quoteTokenAddress": "0x55d398326f99059fF775485246999027B3197955",
                "price": 73440.12,
                "quoteLiquidity": 41.22,
            },
        ]
    }


def _dex_pair_column_names() -> tuple[str, ...]:
    return tuple(
        column.value for column in trading_enums.ExchangeConstantsDexPairsColumns
    )


def _assert_dex_pair_contains_required_columns(dex_pair: dict) -> None:
    for column_name in _dex_pair_column_names():
        assert column_name in dex_pair, (
            f"dex pair missing required column {column_name!r}: {dex_pair!r}"
        )


def _assert_dex_pairs_for_input_symbol(
    body: dict,
    input_symbol: str,
    *,
    min_pair_count: int = 1,
    expected_pair_count: int | None = None,
    min_dex_count: int | None = None,
    expected_dex: str | None = None,
    expected_base_token_address: str | None = None,
    expected_quote_token_address: str | None = None,
) -> None:
    assert input_symbol in body
    dex_pairs: list = body[input_symbol]
    if expected_pair_count is not None:
        assert len(dex_pairs) == expected_pair_count
    else:
        assert len(dex_pairs) >= min_pair_count
    dex_pairs_columns = trading_enums.ExchangeConstantsDexPairsColumns
    dex_column = dex_pairs_columns.DEX.value
    for dex_pair in dex_pairs:
        _assert_dex_pair_contains_required_columns(dex_pair)
        if expected_base_token_address is not None:
            assert dex_pair[dex_pairs_columns.BASE_TOKEN_ADDRESS.value].lower() == expected_base_token_address.lower()
        if expected_quote_token_address is not None:
            assert dex_pair[dex_pairs_columns.QUOTE_TOKEN_ADDRESS.value].lower() == expected_quote_token_address.lower()
    if min_dex_count is not None:
        assert len({dex_pair[dex_column] for dex_pair in dex_pairs}) >= min_dex_count
    if expected_dex is not None:
        assert all(dex_pair[dex_column] == expected_dex for dex_pair in dex_pairs)


def _dexscreener_query_params(symbols: list[str] | None = None) -> list[tuple[str, typing.Any]]:
    requested_symbols = symbols or [DEX_BTCB_USDT]
    params: list[tuple[str, typing.Any]] = [
        ("id", "dexscreener-config"),
        ("name", "dexscreener-test"),
        ("exchange", "dexscreener"),
        ("sandboxed", False),
        ("trading_type", protocol_models.TradingType.SPOT.value),
    ]
    params.extend(("symbols", symbol) for symbol in requested_symbols)
    return params


def _defillama_query_params(symbols: list[str] | None = None) -> list[tuple[str, typing.Any]]:
    requested_symbols = symbols or [DEX_BTCB_USDT_ADDRESS_BEP20]
    params: list[tuple[str, typing.Any]] = [
        ("id", "defillama-config"),
        ("name", "defillama-test"),
        ("exchange", "defillama"),
        ("sandboxed", False),
        ("trading_type", protocol_models.TradingType.SPOT.value),
    ]
    params.extend(("symbols", symbol) for symbol in requested_symbols)
    return params


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


class TestExchangesGetDexPairs:
    def test_returns_dex_pairs_grouped_by_symbol(
        self,
        client: typing.Any,
    ) -> None:
        expected = _mock_dex_pairs_payload()
        with mock.patch.object(
            node_exchanges_core,
            "get_dex_pairs_for_symbols",
            mock.AsyncMock(return_value=expected),
        ) as get_dex_pairs_mock:
            response = client.get(
                _DEX_PAIRS,
                params={
                    "id": "dexscreener-config",
                    "name": "dexscreener-test",
                    "exchange": "dexscreener",
                    "sandboxed": False,
                    "trading_type": "spot",
                    "symbols": "BTCB/USDT",
                },
            )
            get_dex_pairs_mock.assert_awaited_once()
            assert response.status_code == 200
            assert response.json() == expected
            assert_response_headers(response)

    def test_returns_400_when_symbols_missing(
        self,
        client: typing.Any,
    ) -> None:
        with mock.patch.object(
            node_exchanges_core,
            "get_dex_pairs_for_symbols",
            mock.AsyncMock(),
        ) as get_dex_pairs_mock:
            response = client.get(
                _DEX_PAIRS,
                params={
                    "id": "dexscreener-config",
                    "name": "dexscreener-test",
                    "exchange": "dexscreener",
                    "sandboxed": False,
                    "trading_type": "spot",
                },
            )
            get_dex_pairs_mock.assert_not_called()
            assert response.status_code == 400
            assert response.json() == {"error": "symbols query parameter is required"}

    def test_returns_501_when_ob_fetch_dex_pairs_not_supported(
        self,
        client: typing.Any,
    ) -> None:
        not_supported_error = trading_errors.NotSupported(
            "This exchange doesn't support obFetchDexPairs"
        )
        with mock.patch.object(
            node_exchanges_core,
            "get_dex_pairs_for_symbols",
            mock.AsyncMock(side_effect=not_supported_error),
        ):
            response = client.get(
                _DEX_PAIRS,
                params={
                    "id": "binance-config",
                    "name": "binance-test",
                    "exchange": "binance",
                    "sandboxed": False,
                    "trading_type": "spot",
                    "symbols": "BTC/USDT",
                },
            )
            assert response.status_code == 501
            assert response.json() == {"error": str(not_supported_error)}


class TestExchangesDexPairsIntegration:
    def test_dexscreener_different_pairs_returns_multiple_venues(
        self,
        client: typing.Any,
    ) -> None:
        requested_symbols = [
            DEX_BTCB_USDT,
            DEX_BTCB_USDT_ANY_BEP20_DEX,
            DEX_BTCB_USDT_BEP20_UNISWAP,
            DEX_BTCB_USDT_ADDRESS_ANY_BEP20_DEX,
        ]
        response = client.get(_DEX_PAIRS, params=_dexscreener_query_params(requested_symbols))
        assert response.status_code == 200
        body: dict = response.json()
        assert set(body.keys()) == set(requested_symbols)
        _assert_dex_pairs_for_input_symbol(body, DEX_BTCB_USDT, min_pair_count=2, min_dex_count=2)
        _assert_dex_pairs_for_input_symbol(body, DEX_BTCB_USDT_ANY_BEP20_DEX, min_pair_count=2, min_dex_count=2)
        _assert_dex_pairs_for_input_symbol(
            body,
            DEX_BTCB_USDT_BEP20_UNISWAP,
            min_pair_count=1,
            expected_dex=UNISWAP_DEX,
        )
        _assert_dex_pairs_for_input_symbol(
            body,
            DEX_BTCB_USDT_ADDRESS_ANY_BEP20_DEX,
            min_pair_count=2,
            min_dex_count=2,
            expected_base_token_address=BTCB_BSC_TOKEN_ADDRESS,
            expected_quote_token_address=USDT_BSC_TOKEN_ADDRESS,
        )
        assert_response_headers(response)

    def test_defillama_address_pairs_return_wildcard_venue(
        self,
        client: typing.Any,
    ) -> None:
        requested_symbols = [
            DEX_BTCB_USDT_ADDRESS_BEP20,
            DEX_BTCB_USDT_ADDRESS_ANY_BEP20_DEX,
        ]
        response = client.get(_DEX_PAIRS, params=_defillama_query_params(requested_symbols))
        assert response.status_code == 200
        body: dict = response.json()
        assert set(body.keys()) == set(requested_symbols)
        for input_symbol in requested_symbols:
            _assert_dex_pairs_for_input_symbol(
                body,
                input_symbol,
                expected_pair_count=1,
                expected_dex=octobot_commons.ANY_DEX_WILDCARD,
                expected_base_token_address=BTCB_BSC_TOKEN_ADDRESS,
                expected_quote_token_address=USDT_BSC_TOKEN_ADDRESS,
            )
        assert_response_headers(response)
