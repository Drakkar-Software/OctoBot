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

#  Functional tests for node_api_interface.core.exchanges (real public exchange data; no mocks).
#  Migrated from simple_market_making_trading_mode TestGetTradedPairs (handler layer → core API).

import os

import decimal
import mock
import octobot_commons
import octobot_commons.constants as commons_constants
import octobot_commons.symbols.symbol_util as commons_symbols
import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums
import pytest

import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges


def _is_github_actions() -> bool:
    return bool(os.getenv("GITHUB_ACTIONS"))


# binanceus works on GitHub CI; binance is used for local runs.
def _public_exchange_name_for_test() -> str:
    return "binanceus" if _is_github_actions() else "binance"


LIQUID_TEST_SYMBOL = "BTC/USDT"
DEXSCREENER_EXCHANGE_NAME = "dexscreener"
DEX_BTCB_USDT = "BTCB/USDT"
DEX_WBNB_USDT = "WBNB/USDT"
BSC_NETWORK = "BEP20"
UNISWAP_DEX = "UNISWAP"
PANCAKESWAP_DEX = "PANCAKESWAP"
DEX_SUFFIX = (
    f"{octobot_commons.NETWORK_SEPARATOR}{BSC_NETWORK}"
    f"{octobot_commons.DEX_SEPARATOR}{UNISWAP_DEX}"
)
ANY_DEX_SUFFIX = (
    f"{octobot_commons.NETWORK_SEPARATOR}{BSC_NETWORK}"
    f"{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"
)


def _spot_exchange_config() -> protocol_models.ExchangeConfig:
    exchange_name = _public_exchange_name_for_test()
    return protocol_models.ExchangeConfig(
        id="test-exchange-config",
        name=f"{exchange_name}-test",
        exchange=exchange_name,
        sandboxed=False,
    )


def _dexscreener_exchange_config() -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id="dexscreener-config",
        name="dexscreener-test",
        exchange=DEXSCREENER_EXCHANGE_NAME,
        sandboxed=False,
    )


def _dex_pair_column_names() -> tuple[str, ...]:
    return tuple(
        column.value for column in trading_enums.ExchangeConstantsDexPairsColumns
    )


def _assert_dex_pair_contains_required_columns(dex_pair: dict) -> None:
    for column_name in _dex_pair_column_names():
        assert column_name in dex_pair, (
            f"dex pair missing required column {column_name!r}: {dex_pair!r}"
        )


def _mock_dex_pair(
    symbol: str,
    network: str,
    dex: str,
    *,
    base_token_address: str = "0xbase",
    quote_token_address: str = "0xquote",
) -> dict:
    return {
        trading_enums.ExchangeConstantsDexPairsColumns.SYMBOL.value: symbol,
        trading_enums.ExchangeConstantsDexPairsColumns.NETWORK.value: network,
        trading_enums.ExchangeConstantsDexPairsColumns.DEX.value: dex,
        trading_enums.ExchangeConstantsDexPairsColumns.BASE_TOKEN_ADDRESS.value: base_token_address,
        trading_enums.ExchangeConstantsDexPairsColumns.QUOTE_TOKEN_ADDRESS.value: quote_token_address,
        trading_enums.ExchangeConstantsDexPairsColumns.PRICE.value: decimal.Decimal("1"),
        trading_enums.ExchangeConstantsDexPairsColumns.QUOTE_LIQUIDITY.value: decimal.Decimal("1"),
    }


def _mock_btcb_usdt_dex_pairs() -> list[dict]:
    return [
        _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, PANCAKESWAP_DEX),
        _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, UNISWAP_DEX),
        _mock_dex_pair(DEX_BTCB_USDT, "ETH", UNISWAP_DEX),
    ]


class TestGetTradedPairsAndTimeframesByExchange:
    pytestmark = pytest.mark.asyncio

    async def test_includes_btc_usdt(
        self,
    ) -> None:
        public_name = _public_exchange_name_for_test()
        config = _spot_exchange_config()
        result = await exchanges.get_traded_pairs_and_timeframes_by_exchange(config)
        assert public_name in result
        pair_key = exchanges.ExchangeInfo.PAIRS.value
        assert pair_key in result[public_name]
        pairs_list = result[public_name][pair_key]
        assert isinstance(pairs_list, list)
        assert len(pairs_list) > 0
        assert LIQUID_TEST_SYMBOL in pairs_list
        for traded_symbol in pairs_list:
            assert commons_symbols.parse_symbol(traded_symbol).is_spot(), (
                f"with default spot exchange type, only spot pairs are returned; got {traded_symbol!r}"
            )

    async def test_futures_trading_type_uses_future_exchange_type(
        self,
    ) -> None:
        config = _spot_exchange_config()
        profile_data = exchanges._get_exchange_profile_data(
            config,
            trading_type=protocol_models.TradingType.FUTURES,
        )
        assert profile_data.exchanges[0].exchange_type == commons_constants.CONFIG_EXCHANGE_FUTURE


class TestDexPairsForInputSymbol:
    def test_plain_trading_pair_returns_all_matching_dex_pairs(self) -> None:
        dex_pairs = _mock_btcb_usdt_dex_pairs()
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(dex_pairs, DEX_BTCB_USDT)
        assert matching_dex_pairs == dex_pairs

    def test_network_suffix_filters_by_network(self) -> None:
        dex_pairs = _mock_btcb_usdt_dex_pairs()
        input_symbol = f"{DEX_BTCB_USDT}{octobot_commons.NETWORK_SEPARATOR}{BSC_NETWORK}"
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(dex_pairs, input_symbol)
        assert matching_dex_pairs == [
            _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, PANCAKESWAP_DEX),
            _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, UNISWAP_DEX),
        ]

    def test_network_and_dex_suffix_filters_by_network_and_dex(self) -> None:
        dex_pairs = _mock_btcb_usdt_dex_pairs()
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(
            dex_pairs,
            f"{DEX_BTCB_USDT}{DEX_SUFFIX}",
        )
        assert matching_dex_pairs == [_mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, UNISWAP_DEX)]

    def test_any_dex_suffix_matches_all_dexes_on_network(self) -> None:
        dex_pairs = _mock_btcb_usdt_dex_pairs()
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(
            dex_pairs,
            f"{DEX_BTCB_USDT}{ANY_DEX_SUFFIX}",
        )
        assert matching_dex_pairs == [
            _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, PANCAKESWAP_DEX),
            _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, UNISWAP_DEX),
        ]

    def test_excludes_non_matching_base_or_quote(self) -> None:
        dex_pairs = _mock_btcb_usdt_dex_pairs()
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(dex_pairs, DEX_WBNB_USDT)
        assert matching_dex_pairs == []

    def test_contract_address_pair_matches_by_token_addresses(self) -> None:
        btcb_address = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
        usdt_address = "0x55d398326f99059fF775485246999027B3197955"
        address_pair = f"{btcb_address}/{usdt_address}"
        dex_pairs = [
            _mock_dex_pair(
                DEX_BTCB_USDT,
                BSC_NETWORK,
                PANCAKESWAP_DEX,
                base_token_address=btcb_address,
                quote_token_address=usdt_address,
            ),
            _mock_dex_pair(
                DEX_BTCB_USDT,
                BSC_NETWORK,
                UNISWAP_DEX,
                base_token_address=btcb_address,
                quote_token_address=usdt_address,
            ),
            _mock_dex_pair(DEX_BTCB_USDT, "ETH", UNISWAP_DEX),
        ]
        matching_dex_pairs = exchanges.dex_pairs_for_input_symbol(
            dex_pairs,
            f"{address_pair}{ANY_DEX_SUFFIX}",
        )
        assert matching_dex_pairs == dex_pairs[:2]


class TestGetDexPairsForSymbols:
    pytestmark = pytest.mark.asyncio

    async def test_delegates_to_exchange_get_dex_pairs_and_groups_by_input_symbol(self) -> None:
        config = _dexscreener_exchange_config()
        flat_dex_pairs = _mock_btcb_usdt_dex_pairs()
        exchange_mock = mock.Mock()
        exchange_mock.get_dex_pairs = mock.AsyncMock(return_value=flat_dex_pairs)
        exchange_manager_mock = mock.Mock()
        exchange_manager_mock.exchange = exchange_mock
        context_manager_mock = mock.MagicMock()
        context_manager_mock.__aenter__ = mock.AsyncMock(return_value=exchange_manager_mock)
        context_manager_mock.__aexit__ = mock.AsyncMock(return_value=False)
        with mock.patch(
            "octobot_trading.exchanges.exchange_manager_from_exchange_data",
            return_value=context_manager_mock,
        ):
            result = await exchanges.get_dex_pairs_for_symbols(config, [DEX_BTCB_USDT])
        exchange_mock.get_dex_pairs.assert_awaited_once_with([DEX_BTCB_USDT])
        assert result == {DEX_BTCB_USDT: flat_dex_pairs}

    async def test_delegates_two_symbols_and_groups_batch_result(self) -> None:
        config = _dexscreener_exchange_config()
        requested_symbols = [DEX_BTCB_USDT, DEX_WBNB_USDT]
        flat_dex_pairs = [
            _mock_dex_pair(DEX_BTCB_USDT, BSC_NETWORK, PANCAKESWAP_DEX),
            _mock_dex_pair(DEX_WBNB_USDT, BSC_NETWORK, PANCAKESWAP_DEX),
        ]
        exchange_mock = mock.Mock()
        exchange_mock.get_dex_pairs = mock.AsyncMock(return_value=flat_dex_pairs)
        exchange_manager_mock = mock.Mock()
        exchange_manager_mock.exchange = exchange_mock
        context_manager_mock = mock.MagicMock()
        context_manager_mock.__aenter__ = mock.AsyncMock(return_value=exchange_manager_mock)
        context_manager_mock.__aexit__ = mock.AsyncMock(return_value=False)
        with mock.patch(
            "octobot_trading.exchanges.exchange_manager_from_exchange_data",
            return_value=context_manager_mock,
        ):
            result = await exchanges.get_dex_pairs_for_symbols(config, requested_symbols)
        exchange_mock.get_dex_pairs.assert_awaited_once_with(requested_symbols)
        assert result == {
            DEX_BTCB_USDT: [flat_dex_pairs[0]],
            DEX_WBNB_USDT: [flat_dex_pairs[1]],
        }

    async def test_dexscreener_btcb_usdt_returns_multiple_venues(self) -> None:
        config = _dexscreener_exchange_config()
        result = await exchanges.get_dex_pairs_for_symbols(config, [DEX_BTCB_USDT])
        dex_pairs = result[DEX_BTCB_USDT]
        assert len(dex_pairs) >= 2
        for dex_pair in dex_pairs:
            _assert_dex_pair_contains_required_columns(dex_pair)
        dexes = {
            dex_pair[trading_enums.ExchangeConstantsDexPairsColumns.DEX.value]
            for dex_pair in dex_pairs
        }
        assert len(dexes) >= 2


class TestExchangeTypeFromTradingType:
    def test_spot_trading_type_maps_to_spot_exchange_type(self) -> None:
        assert (
            exchanges.exchange_type_from_trading_type(protocol_models.TradingType.SPOT)
            == commons_constants.CONFIG_EXCHANGE_SPOT
        )

    def test_futures_trading_type_maps_to_future_exchange_type(self) -> None:
        assert (
            exchanges.exchange_type_from_trading_type(protocol_models.TradingType.FUTURES)
            == commons_constants.CONFIG_EXCHANGE_FUTURE
        )
