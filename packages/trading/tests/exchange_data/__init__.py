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

# avoid circular imports when launching tests from this folder
import octobot_trading.api  # TODO fix circular import when importing octobot_trading.exchange_data first

from octobot_trading.exchange_data.prices.price_events_manager import PriceEventsManager
from octobot_trading.exchange_data.prices.prices_manager import PricesManager
from octobot_trading.exchange_data.recent_trades.recent_trades_manager import RecentTradesManager


@pytest.fixture()
def price_events_manager(event_loop):
    return PriceEventsManager()


@pytest.fixture()
def prices_manager(event_loop, backtesting_exchange_manager):
    return PricesManager(backtesting_exchange_manager, "BTC/USDT")


@pytest.fixture()
def recent_trades_manager(event_loop):
    return RecentTradesManager()
