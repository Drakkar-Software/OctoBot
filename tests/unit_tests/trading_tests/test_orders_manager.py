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

from config import CONFIG_ENABLED_OPTION, CONFIG_TRADER
from octobot_trading.exchanges.exchange_manager import ExchangeManager
from tests.test_utils.config import load_test_config
from trading.trader.trader import Trader
from trading.trader.trader_simulator import TraderSimulator
from trading.trader.order import BuyLimitOrder, StopLossOrder, StopLossLimitOrder


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestOrdersManagers:
    @staticmethod
    async def init_default():
        config = load_test_config()
        config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = True
        exchange_manager = ExchangeManager(config, ccxt.binance, is_simulated=True)
        await exchange_manager.initialize()
        exchange_inst = exchange_manager.get_exchange()
        trader_real_inst = Trader(config, exchange_inst, 1)
        trader_simulator_inst = TraderSimulator(config, exchange_inst, 1)
        order_manager_inst = trader_real_inst.get_order_manager()
        order_manager_simulator_inst = trader_simulator_inst.get_order_manager()
        return config, exchange_inst, trader_real_inst, order_manager_inst, trader_simulator_inst, \
            order_manager_simulator_inst

    @staticmethod
    def stop(trader):
        trader.stop_order_manager()

    async def test_add_remove_order_to_list(self):
        _, _, trader_inst, order_manager_inst, trader_simulator_inst, \
            order_manager_simulator_inst = await self.init_default()

        # real trader

        assert len(order_manager_inst.get_open_orders()) == 0

        r_order1 = BuyLimitOrder(trader_inst)
        r_order1.order_id = 1
        r_order2 = StopLossOrder(trader_inst)
        r_order1.add_linked_order(r_order2)
        r_order2.add_linked_order(r_order1)
        # add both
        order_manager_inst.add_order_to_list(r_order1)
        order_manager_inst.add_order_to_list(r_order2)
        assert len(order_manager_inst.get_open_orders()) == 2

        r_order3 = BuyLimitOrder(trader_inst)
        r_order3.order_id = 3
        r_order4 = StopLossLimitOrder(trader_inst)
        r_order3.add_linked_order(r_order4)
        r_order4.add_linked_order(r_order3)
        # add both
        order_manager_inst.add_order_to_list(r_order3)
        order_manager_inst.add_order_to_list(r_order4)
        assert len(order_manager_inst.get_open_orders()) == 4

        # add none
        order_manager_inst.add_order_to_list(r_order3)
        order_manager_inst.add_order_to_list(r_order4)
        order_manager_inst.add_order_to_list(r_order1)
        order_manager_inst.add_order_to_list(r_order2)
        assert len(order_manager_inst.get_open_orders()) == 4

        # now remove
        assert order_manager_inst._already_has_real_or_linked_order(r_order2)
        assert order_manager_inst._order_in_list(r_order2)
        order_manager_inst.remove_order_from_list(r_order2)
        assert not order_manager_inst._already_has_real_or_linked_order(r_order2)
        assert not order_manager_inst._order_in_list(r_order2)
        assert len(order_manager_inst.get_open_orders()) == 3
        assert order_manager_inst._already_has_real_or_linked_order(r_order1)
        order_manager_inst.remove_order_from_list(r_order1)
        assert not order_manager_inst._already_has_real_or_linked_order(r_order1)
        assert len(order_manager_inst.get_open_orders()) == 2

        assert order_manager_inst._already_has_real_or_linked_order(r_order3)
        order_manager_inst.remove_order_from_list(r_order3)
        assert not order_manager_inst._already_has_real_or_linked_order(r_order3)
        assert len(order_manager_inst.get_open_orders()) == 1
        assert order_manager_inst._already_has_real_or_linked_order(r_order4)
        assert order_manager_inst._order_in_list(r_order4)
        order_manager_inst.remove_order_from_list(r_order4)
        assert not order_manager_inst._already_has_real_or_linked_order(r_order4)
        assert not order_manager_inst._order_in_list(r_order4)
        assert len(order_manager_inst.get_open_orders()) == 0

        # simulated trader

        assert len(order_manager_simulator_inst.get_open_orders()) == 0

        r_order11 = BuyLimitOrder(trader_simulator_inst)
        r_order12 = StopLossOrder(trader_simulator_inst)
        r_order11.add_linked_order(r_order12)
        r_order12.add_linked_order(r_order11)
        # add both
        order_manager_simulator_inst.add_order_to_list(r_order11)
        order_manager_simulator_inst.add_order_to_list(r_order12)
        assert len(order_manager_simulator_inst.get_open_orders()) == 2

        r_order13 = BuyLimitOrder(trader_simulator_inst)
        r_order14 = StopLossLimitOrder(trader_simulator_inst)
        r_order13.add_linked_order(r_order14)
        r_order14.add_linked_order(r_order13)
        # add both
        order_manager_simulator_inst.add_order_to_list(r_order13)
        order_manager_simulator_inst.add_order_to_list(r_order14)
        assert len(order_manager_simulator_inst.get_open_orders()) == 4

        # add none
        order_manager_simulator_inst.add_order_to_list(r_order13)
        order_manager_simulator_inst.add_order_to_list(r_order14)
        order_manager_simulator_inst.add_order_to_list(r_order11)
        order_manager_simulator_inst.add_order_to_list(r_order12)
        assert len(order_manager_simulator_inst.get_open_orders()) == 4

        # now remove

        assert not order_manager_inst._order_in_list(r_order13)
        assert not order_manager_inst._order_in_list(r_order14)
        assert not order_manager_inst._order_in_list(r_order11)
        assert not order_manager_inst._order_in_list(r_order12)

        assert order_manager_simulator_inst._order_in_list(r_order11)
        order_manager_simulator_inst.remove_order_from_list(r_order11)
        assert len(order_manager_simulator_inst.get_open_orders()) == 3
        assert not order_manager_simulator_inst._order_in_list(r_order11)
        order_manager_simulator_inst.remove_order_from_list(r_order12)
        assert len(order_manager_simulator_inst.get_open_orders()) == 2
        order_manager_simulator_inst.remove_order_from_list(r_order14)
        assert len(order_manager_simulator_inst.get_open_orders()) == 1
        assert order_manager_simulator_inst._order_in_list(r_order13)
        order_manager_simulator_inst.remove_order_from_list(r_order13)
        assert len(order_manager_simulator_inst.get_open_orders()) == 0
        assert not order_manager_simulator_inst._order_in_list(r_order13)

    async def test_update_last_symbol_list(self):
        pass

    async def test_update_last_symbol_prices(self):
        pass

    async def test_in_run(self):
        await self.init_default()
