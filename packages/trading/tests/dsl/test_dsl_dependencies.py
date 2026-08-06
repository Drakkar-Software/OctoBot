#  Drakkar-Software OctoBot-Trading
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
import mock

import octobot_trading.dsl.dsl_dependencies as dsl_dependencies


class TestResolveSymbol:
    def test_keeps_symbol_when_exchange_lookup_returns_none(self):
        dependency = dsl_dependencies.SymbolDependency(symbol="BTC/USDT")
        exchange_manager = mock.Mock()
        exchange_manager.get_exchange_symbol = mock.Mock(return_value=None)

        dependency.resolve_symbol(exchange_manager)

        assert dependency.symbol == "BTC/USDT"
        assert dependency.alias is None
        exchange_manager.get_exchange_symbol.assert_called_once_with(
            "BTC/USDT", error_on_missing=False
        )

    def test_sets_alias_when_exchange_returns_unified_symbol(self):
        dependency = dsl_dependencies.SymbolDependency(symbol="btc/usdt")
        exchange_manager = mock.Mock()
        exchange_manager.get_exchange_symbol = mock.Mock(return_value="BTC/USDT")

        dependency.resolve_symbol(exchange_manager)

        assert dependency.symbol == "BTC/USDT"
        assert dependency.alias == "btc/usdt"
