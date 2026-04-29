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
import os
import time

import pytest

import octobot_trading.enums as enums
import octobot_trading.personal_data.positions.positions_manager as positions_mgr
from octobot_trading.personal_data import SellMarketOrder
from tests.exchanges import future_simulated_exchange_manager
from tests.exchanges.traders import future_trader_simulator_with_default_linear, DEFAULT_FUTURE_SYMBOL
from tests import event_loop

# All test coroutines will be treated as marked.
from tests.personal_data import DEFAULT_MARKET_QUANTITY
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity

pytestmark = pytest.mark.asyncio


async def test_get_symbol_position(future_trader_simulator_with_default_linear):
    config, exchange_manager, trader, default_contract = future_trader_simulator_with_default_linear
    positions_manager = exchange_manager.exchange_personal_data.positions_manager
    symbol_contract = default_contract
    trader.exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL,  default_contract)

    p1 = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=None)
    assert p1
    p1bis = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=None)
    assert p1 is p1bis

    p2 = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=enums.PositionSide.LONG)
    assert p2
    p2bis = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=enums.PositionSide.SHORT)
    assert p2 is not p2bis


async def test_get_symbol_positions(future_trader_simulator_with_default_linear):
    config, exchange_manager, trader, default_contract = future_trader_simulator_with_default_linear
    positions_manager = exchange_manager.exchange_personal_data.positions_manager
    symbol_contract = default_contract
    trader.exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL, 
                                                              default_contract)

    symbol_contract.set_position_mode(is_one_way=False)
    assert len(positions_manager.get_symbol_positions(symbol=DEFAULT_FUTURE_SYMBOL)) == 0
    p1 = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=enums.PositionSide.LONG)
    assert len(positions_manager.get_symbol_positions(symbol=DEFAULT_FUTURE_SYMBOL)) == 1
    p2 = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=enums.PositionSide.SHORT)
    assert len(positions_manager.get_symbol_positions(symbol=DEFAULT_FUTURE_SYMBOL)) == 2
    assert positions_manager.get_symbol_positions(symbol=DEFAULT_FUTURE_SYMBOL) == [p2, p1]


async def test_get_order_position(future_trader_simulator_with_default_linear):
    config, exchange_manager, trader, default_contract = future_trader_simulator_with_default_linear
    positions_manager = exchange_manager.exchange_personal_data.positions_manager
    symbol_contract = default_contract
    trader.exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL, 
                                                              default_contract)

    p1 = positions_manager.get_symbol_position(symbol=DEFAULT_FUTURE_SYMBOL, side=enums.PositionSide.BOTH)
    market_sell = SellMarketOrder(trader)
    market_sell.update(order_type=enums.TraderOrderType.SELL_MARKET,
                       symbol=DEFAULT_FUTURE_SYMBOL,
                       position_side=enums.PositionSide.SHORT)
    p1bis = positions_manager.get_order_position(market_sell, contract=symbol_contract)
    assert p1 is p1bis


async def test__generate_position_id(future_trader_simulator_with_default_linear):
    config, exchange_manager, trader, default_contract = future_trader_simulator_with_default_linear
    positions_manager = exchange_manager.exchange_personal_data.positions_manager
    symbol_contract = default_contract
    trader.exchange_manager.exchange.set_pair_future_contract(DEFAULT_FUTURE_SYMBOL, 
                                                              default_contract)

    if not os.getenv('CYTHON_IGNORE'):
        sep = positions_mgr.PositionsManager.POSITION_ID_SEPARATOR
        current_time = time.time()
        symbol_contract.set_position_mode(is_one_way=True)
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, None) == DEFAULT_FUTURE_SYMBOL
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, None, None) == DEFAULT_FUTURE_SYMBOL
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, None, expiration_time=current_time) == \
               DEFAULT_FUTURE_SYMBOL + sep + str(current_time)
        symbol_contract.set_position_mode(is_one_way=False)
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, enums.PositionSide.LONG) == \
               DEFAULT_FUTURE_SYMBOL + sep + enums.PositionSide.LONG.value
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, enums.PositionSide.LONG, current_time) == \
               DEFAULT_FUTURE_SYMBOL + sep + str(current_time) + sep + enums.PositionSide.LONG.value
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, enums.PositionSide.SHORT) == \
               DEFAULT_FUTURE_SYMBOL + sep + enums.PositionSide.SHORT.value
        assert positions_manager._position_id_factory(DEFAULT_FUTURE_SYMBOL, enums.PositionSide.SHORT, current_time) == \
               DEFAULT_FUTURE_SYMBOL + sep + str(current_time) + sep + enums.PositionSide.SHORT.value
