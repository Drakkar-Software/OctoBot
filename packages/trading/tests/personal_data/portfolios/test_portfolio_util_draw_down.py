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
import decimal
import pytest

import octobot_commons.constants as commons_constants
import octobot_trading.personal_data as personal_data

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

pytestmark = pytest.mark.asyncio

DAY = commons_constants.DAYS_TO_SECONDS


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot"], indirect=True)
async def test_get_draw_down_spot_from_portfolio_value_history(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    value_holder = portfolio_manager.portfolio_value_holder
    history_manager = portfolio_manager.historical_portfolio_value_manager
    assert history_manager is not None
    reference_market = portfolio_manager.reference_market
    time_manager = exchange_manager.backtesting.time_manager
    start_time = 1_700_006_400  # a day start

    value_holder.portfolio_origin_value = decimal.Decimal(1000)
    # the portfolio rises to 1200, falls to 900, then ends at 970
    for day, value in enumerate((1100, 1200, 900)):
        time_manager.current_timestamp = start_time + day * DAY
        await history_manager.on_new_value(
            time_manager.current_timestamp, {reference_market: decimal.Decimal(value)}, save_changes=False
        )
    time_manager.current_timestamp = start_time + 3 * DAY
    value_holder.portfolio_current_value = decimal.Decimal(970)
    assert len(history_manager.historical_portfolio_value) == 3

    # lowest point 900 after a 1200 peak: 25% draw down
    assert personal_data.get_draw_down(exchange_manager) == decimal.Decimal(25)


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot"], indirect=True)
async def test_get_draw_down_spot_without_history(backtesting_trader):
    _, exchange_manager, _ = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_manager.historical_portfolio_value_manager = None
    portfolio_manager.portfolio_value_holder.portfolio_origin_value = decimal.Decimal(1000)
    portfolio_manager.portfolio_value_holder.portfolio_current_value = decimal.Decimal(970)

    assert personal_data.get_draw_down(exchange_manager) == decimal.Decimal(3)

    # a run that only gained has no draw down
    portfolio_manager.portfolio_value_holder.portfolio_current_value = decimal.Decimal(1100)
    assert personal_data.get_draw_down(exchange_manager) == decimal.Decimal(0)
