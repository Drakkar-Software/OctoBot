#  Drakkar-Software OctoBot
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


import ccxt
import pytest

from trading.exchanges.exchange_manager import ExchangeManager
from config import *
from tests.test_utils.config import load_test_config
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.trade import Trade
from trading.trader.order import SellLimitOrder


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def init_default():
    config = load_test_config()
    exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
    await exchange_manager.initialize()
    exchange_inst = exchange_manager.get_exchange()
    trader_inst = TraderSimulator(config, exchange_inst, 1)
    await trader_inst.portfolio.initialize()
    trades_manager_inst = trader_inst.get_trades_manager()
    await trades_manager_inst.initialize()
    trader_inst.stop_order_manager()
    return config, exchange_inst, trader_inst, trades_manager_inst


async def test_as_dict():
    _, exchange_inst, trader_inst, trades_manager_inst = await init_default()
    symbol = "BTC/USD"
    new_order = SellLimitOrder(trader_inst)
    new_order.new(TraderOrderType.SELL_LIMIT, symbol, 90, 4, 90)
    new_order.fee = {
        FeePropertyColumns.COST.value: 100,
        FeePropertyColumns.CURRENCY.value: "BTC"
    }
    new_order.filled_price = 898
    new_order.total_cost = 10
    new_order.order_id = 101
    new_order.creation_time = 42
    new_order.canceled_time = 1010
    new_order.executed_time = 10101
    new_trade = Trade(exchange_inst, new_order)
    trade_dict = new_trade.as_dict()
    trade_dict.pop('exchange')
    assert trade_dict == {
        'order': None,
        'from_previous_execution': False,
        'currency': 'BTC',
        'market': 'USD',
        'quantity': 4,
        'price': 898,
        'cost': 10,
        'order_type': 'SELL_LIMIT',
        'final_status': 'OPEN',
        'fee': {
            'cost': 100,
            'currency': 'BTC'
        },
        'creation_time': 42,
        'order_id': 101,
        'side': 'SELL',
        'canceled_time': 1010,
        'filled_time': 10101,
        'symbol': 'BTC/USD',
        'simulated': True
    }


async def test_from_dict():
    _, exchange_inst, trader_inst, trades_manager_inst = await init_default()

    # ok case
    trade_dict = {
        'exchange': 'xyz',
        'order': None,
        'from_previous_execution': False,
        'currency': 'BTC',
        'market': 'USD',
        'quantity': 4,
        'price': 898,
        'cost': 10,
        'order_type': 'SELL_LIMIT',
        'final_status': 'OPEN',
        'fee': {
            'cost': 100,
            'currency': 'BTC'
        },
        'creation_time': 42,
        'order_id': 101,
        'side': 'SELL',
        'canceled_time': 1010,
        'filled_time': 10101,
        'symbol': 'BTC/USD',
        'simulated': True
    }
    new_trade = Trade.from_dict(exchange_inst, trade_dict)
    assert new_trade.exchange == exchange_inst
    assert new_trade.order is None
    assert new_trade.from_previous_execution is True
    assert new_trade.currency == 'BTC'
    assert new_trade.market == 'USD'
    assert new_trade.price == 898
    assert new_trade.cost == 10
    assert new_trade.order_type == TraderOrderType.SELL_LIMIT
    assert new_trade.final_status == OrderStatus.OPEN
    assert new_trade.fee == {
        'cost': 100,
        'currency': 'BTC'
    }
    assert new_trade.creation_time == 42
    assert new_trade.order_id == 101
    assert new_trade.side == TradeOrderSide.SELL
    assert new_trade.canceled_time == 1010
    assert new_trade.filled_time == 10101
    assert new_trade.symbol == 'BTC/USD'
    assert new_trade.simulated is True

    # not ok cases
    with pytest.raises(RuntimeError):
        trade_dict.pop('exchange')
        Trade.from_dict(exchange_inst, trade_dict)
        trade_dict['exchange'] = None

    with pytest.raises(RuntimeError):
        trade_dict.pop('order_id')
        Trade.from_dict(exchange_inst, trade_dict)
