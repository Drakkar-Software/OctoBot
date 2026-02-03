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

from tests.test_utils.random_numbers import random_quantity, decimal_random_quantity
from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_init_profitability(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_profitability = portfolio_manager.portfolio_profitability
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    assert portfolio_profitability.profitability == 0
    assert portfolio_profitability.profitability_percent == 0
    assert portfolio_profitability.profitability_diff == 0
    assert portfolio_profitability.market_profitability_percent == 0
    assert portfolio_profitability.initial_portfolio_current_profitability == 0
    assert portfolio_value_holder.portfolio_origin_value == 0
    assert portfolio_value_holder.portfolio_current_value == 0


async def test_simple_handle_balance_update(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_profitability = portfolio_manager.portfolio_profitability
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    # set the original values
    portfolio_manager.handle_balance_updated()
    assert portfolio_profitability.profitability == 0
    assert portfolio_profitability.profitability_percent == 0
    assert portfolio_profitability.profitability_diff == 0
    assert portfolio_value_holder.portfolio_origin_value == 10
    assert portfolio_value_holder.portfolio_current_value == 10

    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': 20, 'total': 20},
        'USDT': {'available': 1000, 'total': 1000}
    }, True)
    portfolio_manager.handle_balance_updated()
    assert portfolio_profitability.profitability == 10
    assert portfolio_profitability.profitability_percent == 100
    assert portfolio_profitability.profitability_diff == 100
    assert portfolio_value_holder.portfolio_origin_value == 10
    assert portfolio_value_holder.portfolio_current_value == 20


async def test_random_quantity_handle_balance_update(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_profitability = portfolio_manager.portfolio_profitability
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    original_symbol_quantity = decimal.Decimal(str(10))

    # set the original values
    portfolio_manager.handle_balance_updated()
    assert portfolio_profitability.profitability == 0
    assert portfolio_profitability.profitability_percent == 0
    assert portfolio_profitability.profitability_diff == 0
    assert portfolio_value_holder.portfolio_origin_value == original_symbol_quantity
    assert portfolio_value_holder.portfolio_current_value == original_symbol_quantity

    new_btc_available = random_quantity(max_value=15)  # shouldn't impact profitability
    new_btc_total = decimal_random_quantity(min_value=new_btc_available, max_value=15)
    new_prof_percent = decimal.Decimal(str((100 * new_btc_total / original_symbol_quantity) - 100))
    portfolio_manager.portfolio.update_portfolio_from_balance({'BTC': {'available': decimal.Decimal(str(new_btc_available)), 'total': new_btc_total}},
                             exchange_manager)
    portfolio_manager.handle_balance_updated()
    assert portfolio_profitability.profitability == new_btc_total - original_symbol_quantity
    assert portfolio_profitability.profitability_percent == new_prof_percent
    assert portfolio_profitability.profitability_diff == new_prof_percent - 0
    assert portfolio_value_holder.portfolio_origin_value == original_symbol_quantity
    assert portfolio_value_holder.portfolio_current_value == new_btc_total

    new_btc_total_2 = decimal_random_quantity(min_value=new_btc_available, max_value=12)
    new_prof_percent_2 = decimal.Decimal(str((100 * new_btc_total_2 / original_symbol_quantity) - 100))
    portfolio_manager.portfolio.update_portfolio_from_balance({'BTC': {'total': new_btc_total_2}}, exchange_manager)
    portfolio_manager.handle_balance_updated()
    assert portfolio_profitability.profitability == new_btc_total_2 - original_symbol_quantity
    assert portfolio_profitability.profitability_percent == new_prof_percent_2
    assert portfolio_profitability.profitability_diff == new_prof_percent_2 - new_prof_percent
    assert portfolio_value_holder.portfolio_origin_value == original_symbol_quantity
    assert portfolio_value_holder.portfolio_current_value == new_btc_total_2
