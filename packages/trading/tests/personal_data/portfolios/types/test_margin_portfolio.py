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
from octobot_commons.constants import PORTFOLIO_AVAILABLE, PORTFOLIO_TOTAL

from octobot_trading.enums import TraderOrderType
from octobot_trading.personal_data.orders.types.limit.sell_limit_order import SellLimitOrder
from octobot_trading.personal_data.orders.types.market.buy_market_order import BuyMarketOrder
from octobot_trading.personal_data.portfolios.types.margin_portfolio import MarginPortfolio

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting, \
    DEFAULT_EXCHANGE_NAME

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("backtesting_exchange_manager", [(None, DEFAULT_EXCHANGE_NAME, False, True, False)],
                         indirect=["backtesting_exchange_manager"])
async def test_initial_portfolio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

    assert isinstance(portfolio_manager.portfolio, MarginPortfolio)
