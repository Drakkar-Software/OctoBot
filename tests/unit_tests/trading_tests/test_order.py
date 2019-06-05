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

import random
import time
import pytest

import ccxt

from octobot_trading.exchanges import ExchangeManager
from config import TradeOrderSide, SIMULATOR_LAST_PRICES_TO_CHECK, TraderOrderType, OrderStatus
from tests.test_utils.config import load_test_config
from trading.trader.order import Order
from trading.trader.trader_simulator import TraderSimulator


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestOrder:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = TraderSimulator(config, exchange_inst, 2)
        order_inst = Order(trader_inst)
        return config, order_inst, trader_inst, exchange_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_get_profitability(self):
        _, _, trader_inst, _ = await self.init_default()

        # Test filled_price > create_last_price
        # test side SELL
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.SELL
        order_filled_sup_side_sell_inst.filled_price = 10
        order_filled_sup_side_sell_inst.created_last_price = 9
        assert order_filled_sup_side_sell_inst.get_profitability() == (-(1 - 10 / 9))

        # test side BUY
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.BUY
        order_filled_sup_side_sell_inst.filled_price = 15.114778
        order_filled_sup_side_sell_inst.created_last_price = 7.265
        assert order_filled_sup_side_sell_inst.get_profitability() == (1 - 15.114778 / 7.265)

        # Test filled_price < create_last_price
        # test side SELL
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.SELL
        order_filled_sup_side_sell_inst.filled_price = 11.556877
        order_filled_sup_side_sell_inst.created_last_price = 20
        assert order_filled_sup_side_sell_inst.get_profitability() == (1 - 20 / 11.556877)

        # test side BUY
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.BUY
        order_filled_sup_side_sell_inst.filled_price = 8
        order_filled_sup_side_sell_inst.created_last_price = 14.35
        assert order_filled_sup_side_sell_inst.get_profitability() == (-(1 - 14.35 / 8))

        # Test filled_price == create_last_price
        # test side SELL
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.SELL
        order_filled_sup_side_sell_inst.filled_price = 1517374.4567
        order_filled_sup_side_sell_inst.created_last_price = 1517374.4567
        assert order_filled_sup_side_sell_inst.get_profitability() == 0

        # test side BUY
        order_filled_sup_side_sell_inst = Order(trader_inst)
        order_filled_sup_side_sell_inst.side = TradeOrderSide.BUY
        order_filled_sup_side_sell_inst.filled_price = 0.4275587387858527
        order_filled_sup_side_sell_inst.created_last_price = 0.4275587387858527
        assert order_filled_sup_side_sell_inst.get_profitability() == 0

        self.stop(trader_inst)

    async def test_check_last_prices(self):
        _, order_inst, trader_inst, _ = await self.init_default()

        # test price in last trades
        # test inferior TRUE
        max_price = 10
        min_price = 4
        order_inst.creation_time = time.time()
        recent_trades = [{"price": random.uniform(min_price, max_price), "timestamp": time.time()}
                         for _ in range(0, SIMULATOR_LAST_PRICES_TO_CHECK)]

        # append validating trade
        recent_trades.append({"price": min_price, "timestamp": time.time()})
        order_inst.last_prices = recent_trades
        assert order_inst.check_last_prices(max_price, inferior=True)

        # test inferior FALSE
        max_price = 10.454677
        min_price = 2.4273
        order_inst.creation_time = time.time()
        recent_trades = [{"price": random.uniform(min_price, max_price), "timestamp": time.time()}
                         for _ in range(0, SIMULATOR_LAST_PRICES_TO_CHECK)]

        # append validating trade
        recent_trades.append({"price": max_price, "timestamp": time.time()})
        order_inst.last_prices = recent_trades
        assert order_inst.check_last_prices(random.uniform(min_price, max_price - 1), inferior=False)

        # test price not in last trades
        # test inferior TRUE
        max_price = 7456.15555632315
        min_price = 1421.1488845
        order_inst.creation_time = time.time()
        recent_trades = [{"price": random.uniform(min_price, max_price), "timestamp": time.time()}
                         for _ in range(0, SIMULATOR_LAST_PRICES_TO_CHECK)]

        order_inst.last_prices = recent_trades
        assert not order_inst.check_last_prices(min_price, inferior=True)

        # test inferior FALSE
        max_price = 0.0001243753
        min_price = 0.000012557753
        order_inst.creation_time = time.time()
        recent_trades = [{"price": random.uniform(min_price, max_price), "timestamp": time.time()}
                         for _ in range(0, SIMULATOR_LAST_PRICES_TO_CHECK)]

        order_inst.last_prices = recent_trades
        assert not order_inst.check_last_prices(max_price, inferior=False)

        self.stop(trader_inst)

    async def test_new(self):
        config, order_inst, trader_inst, exchange_inst = await self.init_default()

        # with real trader
        order_inst.new(TraderOrderType.BUY_MARKET,
                       "BTC/USDT",
                       10000,
                       1,
                       price=None,
                       stop_price=None,
                       order_notifier=None)

        assert order_inst.get_order_type() == TraderOrderType.BUY_MARKET
        assert order_inst.get_order_symbol() == "BTC/USDT"
        assert order_inst.get_create_last_price() == 10000
        assert order_inst.get_origin_quantity() == 1
        assert order_inst.get_creation_time() != 0
        assert order_inst.get_currency_and_market() == ('BTC', 'USDT')
        assert order_inst.get_side() is None
        assert order_inst.get_status() == OrderStatus.OPEN

        order_inst.new(TraderOrderType.STOP_LOSS_LIMIT,
                       "ETH/BTC",
                       0.1,
                       5.2,
                       price=0.12,
                       stop_price=0.9,
                       order_notifier=None)
        assert order_inst.origin_stop_price == 0.9
        assert order_inst.last_prices is None
        assert order_inst.origin_price == 0.12

        # with simulated trader
        trader_sim_inst = TraderSimulator(config, exchange_inst, 1)
        order_sim_inst = Order(trader_sim_inst)

        order_sim_inst.new(TraderOrderType.SELL_MARKET,
                           "LTC/USDT",
                           100,
                           3.22,
                           price=None,
                           stop_price=None,
                           order_notifier=None)
        assert order_sim_inst.get_status() == OrderStatus.OPEN

        self.stop(trader_inst)
        self.stop(trader_sim_inst)
