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
import mock
import pytest

import octobot_trading.personal_data.orders.cancel_policies.expiration_time_order_cancel_policy as expiration_time_order_cancel_policy_import

from tests import event_loop
from tests.exchanges import simulated_exchange_manager
from tests.exchanges.traders import trader_simulator

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestExpirationTimeOrderCancelPolicy:
    """Test the ExpirationTimeOrderCancelPolicy class"""

    async def test_should_cancel_when_expiration_time_reached(self, trader_simulator):
        """Test that should_cancel returns True when expiration time is reached"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        # Set current time to 1000
        current_time = 1000.0
        expiration_time = 1000.0  # Same as current time, should cancel
        
        exchange_mock = mock.Mock()
        exchange_mock.get_exchange_current_time.return_value = current_time
        exchange_manager_inst.exchange = exchange_mock
        
        order = mock.Mock()
        order.is_cleared.return_value = False
        order.trader = trader_inst
        order.trader.exchange_manager = exchange_manager_inst
        
        policy = expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy(
            expiration_time=expiration_time
        )
        
        assert policy.should_cancel(order) is True

    async def test_should_cancel_when_expiration_time_passed(self, trader_simulator):
        """Test that should_cancel returns True when expiration time has passed"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        # Set current time to 2000, expiration was at 1000
        # expiration_time >= current_time: 1000 >= 2000 = False
        current_time = 2000.0
        expiration_time = 1000.0
        
        exchange_mock = mock.Mock()
        exchange_mock.get_exchange_current_time.return_value = current_time
        exchange_manager_inst.exchange = exchange_mock
        
        order = mock.Mock()
        order.is_cleared.return_value = False
        order.trader = trader_inst
        order.trader.exchange_manager = exchange_manager_inst
        
        policy = expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy(
            expiration_time=expiration_time
        )
        
        assert policy.should_cancel(order) is True

    async def test_should_not_cancel_when_expiration_time_not_reached(self, trader_simulator):
        """Test that should_cancel returns False when expiration time has not been reached (expiration in future)"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        # Set current time to 500, expiration is at 1000
        # expiration_time >= current_time: 1000 >= 500 = True
        current_time = 500.0
        expiration_time = 1000.0
        
        exchange_mock = mock.Mock()
        exchange_mock.get_exchange_current_time.return_value = current_time
        exchange_manager_inst.exchange = exchange_mock
        
        order = mock.Mock()
        order.is_cleared.return_value = False
        order.trader = trader_inst
        order.trader.exchange_manager = exchange_manager_inst
        
        policy = expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy(
            expiration_time=expiration_time
        )
        
        assert policy.should_cancel(order) is False

    async def test_should_not_cancel_when_order_cleared(self, trader_simulator):
        """Test that should_cancel returns False when order is cleared"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_time = 1000.0
        expiration_time = 1000.0
        
        exchange_mock = mock.Mock()
        exchange_mock.get_exchange_current_time.return_value = current_time
        exchange_manager_inst.exchange = exchange_mock
        
        order = mock.Mock()
        order.is_cleared.return_value = True  # Order is cleared
        order.trader = trader_inst
        order.trader.exchange_manager = exchange_manager_inst
        
        policy = expiration_time_order_cancel_policy_import.ExpirationTimeOrderCancelPolicy(
            expiration_time=expiration_time
        )
        logger_mock = mock.Mock(error=mock.Mock())
        with mock.patch.object(policy, "get_logger", mock.Mock(return_value=logger_mock)):
            assert policy.should_cancel(order) is False
            # Verify error was logged
            logger_mock.error.assert_called_once()
