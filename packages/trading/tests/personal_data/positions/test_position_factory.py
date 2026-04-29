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
import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data

from tests import event_loop
from tests.exchanges import future_simulated_exchange_manager
from tests.exchanges.traders import future_trader, future_trader_simulator_with_default_linear, DEFAULT_FUTURE_SYMBOL, \
    DEFAULT_FUTURE_SYMBOL_MARGIN_TYPE, DEFAULT_FUTURE_SYMBOL_LEVERAGE, get_default_future_inverse_contract
from tests.test_utils.random_numbers import decimal_random_int, decimal_random_quantity

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_position_instance_from_raw(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear

    raw_position = {
        enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL,
        enums.ExchangeConstantsPositionColumns.STATUS.value: enums.PositionStatus.ADL.value
    }
    position = personal_data.create_position_instance_from_raw(trader_inst, raw_position)
    position_leverage = decimal_random_int(min_value=2, max_value=200)
    position_quantity = decimal_random_quantity(max_value=1000)
    exchange_manager_inst.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL,
                                                            get_default_future_inverse_contract())
    inverse_position_open = personal_data.create_position_instance_from_raw(trader_inst, {
        enums.ExchangeConstantsPositionColumns.SYMBOL.value: DEFAULT_FUTURE_SYMBOL,
        enums.ExchangeConstantsPositionColumns.QUANTITY.value: position_quantity
    })
    assert position.symbol == DEFAULT_FUTURE_SYMBOL
    assert position.market == "USDT"
    assert position.currency == "BTC"
    assert position.status == enums.PositionStatus.ADL
    assert isinstance(position, personal_data.LinearPosition)

    assert inverse_position_open.status == enums.PositionStatus.OPEN
    assert inverse_position_open.quantity == position_quantity
    assert isinstance(inverse_position_open, personal_data.InversePosition)


async def test_create_symbol_position(future_trader_simulator_with_default_linear):
    config, exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    position = personal_data.create_symbol_position(trader_inst, DEFAULT_FUTURE_SYMBOL)
    assert position.symbol == DEFAULT_FUTURE_SYMBOL
