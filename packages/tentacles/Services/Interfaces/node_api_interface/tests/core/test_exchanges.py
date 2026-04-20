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

import octobot_commons.symbols.symbol_util as commons_symbols
import octobot_trading.enums
import pytest

import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges


def _is_github_actions() -> bool:
    return bool(os.getenv("GITHUB_ACTIONS"))


# binanceus works on GitHub CI; binance is used for local runs.
def _public_exchange_name_for_test() -> str:
    return "binanceus" if _is_github_actions() else "binance"


LIQUID_TEST_SYMBOL = "BTC/USDT"
_INVALID_EXCHANGE_TYPE = "not_a_spot_type"

pytestmark = pytest.mark.asyncio


def _spot_exchange_config() -> exchanges.ExchangeConfig:
    return exchanges.ExchangeConfig(
        name=_public_exchange_name_for_test(),
        exchange_type=octobot_trading.enums.ExchangeTypes.SPOT.value,
        sandboxed=False,
    )


class TestGetTradedPairsAndTimeframesByExchange:
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
                f"with exchange_type=spot, only spot pairs are returned; got {traded_symbol!r}"
            )

    def test_accepts_arbitrary_exchange_type_string_on_config(
        self,
    ) -> None:
        config = exchanges.ExchangeConfig.model_validate(
            {
                "name": _public_exchange_name_for_test(),
                "exchange_type": _INVALID_EXCHANGE_TYPE,
                "sandboxed": False,
            }
        )
        assert config.exchange_type == _INVALID_EXCHANGE_TYPE

    def test_rejects_invalid_exchange_type_enum_value(
        self,
    ) -> None:
        with pytest.raises(ValueError):
            octobot_trading.enums.ExchangeTypes(_INVALID_EXCHANGE_TYPE)
