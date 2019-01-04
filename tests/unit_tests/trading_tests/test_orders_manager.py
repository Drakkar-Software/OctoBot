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
from tests.test_utils.config import load_test_config
from trading.trader.trader import Trader


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestOrdersManagers:
    @staticmethod
    async def init_default():
        config = load_test_config()
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_inst = Trader(config, exchange_inst, 1)
        order_manager_inst = trader_inst.get_order_manager()
        return config, exchange_inst, trader_inst, order_manager_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_add_order_to_list(self):
        pass

    async def test_remove_order_from_list(self):
        pass

    async def test_update_last_symbol_list(self):
        pass

    async def test_update_last_symbol_prices(self):
        pass

    async def test_in_run(self):
        await self.init_default()
