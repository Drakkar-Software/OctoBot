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
import pytest
import mock
import pytest_asyncio
import decimal

import octobot_trading.modes.script_keywords as script_keywords


@pytest.fixture
def null_context():
    context = script_keywords.Context(
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    yield context


@pytest_asyncio.fixture
async def mock_context(backtesting_trader):
    _, exchange_manager, trader_inst = backtesting_trader
    context = script_keywords.Context(
        mock.Mock(is_trading_signal_emitter=mock.Mock(return_value=False)),
        exchange_manager,
        trader_inst,
        mock.Mock(),
        "BTC/USDT",
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
        mock.Mock(),
    )
    context.signal_builder = mock.Mock()
    context.is_trading_signal_emitter = mock.Mock(return_value=False)
    context.orders_writer = mock.Mock(log_many=mock.AsyncMock())
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    # init portfolio with 0.5 BTC, 20 ETH and 30000 USDT and only 0.1 available BTC
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("0.1"), 'total': decimal.Decimal("0.5")},
        'ETH': {'available': decimal.Decimal("20"), 'total': decimal.Decimal("20")},
        'USDT': {'available': decimal.Decimal("30000"), 'total': decimal.Decimal("30000")}
    }, True)
    exchange_manager.client_symbols.append("BTC/USDT")
    exchange_manager.client_symbols.append("ETH/USDT")
    exchange_manager.client_symbols.append("ETH/BTC")
    # init prices with BTC/USDT = 40000, ETH/BTC = 0.1 and ETH/USDT = 4000
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("40000")
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/USDT"] = decimal.Decimal("4000")
    portfolio_manager.portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/BTC"] = decimal.Decimal("0.1")
    portfolio_manager.handle_balance_updated()
    yield context
