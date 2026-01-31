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
import decimal

import octobot_trading.personal_data as personal_data
import octobot_trading.personal_data.orders.cancel_policies.chained_order_filling_price_order_cancel_policy as chained_order_filling_price_order_cancel_policy_import
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.enums as enums

from tests import event_loop
from tests.exchanges import simulated_exchange_manager
from tests.exchanges.traders import trader_simulator

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestChainedOrderFillingPriceOrderCancelPolicy:
    """Test the ChainedOrderFillingPriceOrderCancelPolicy class"""

    async def test_should_cancel_when_chained_order_price_reached_trigger_above(self, trader_simulator):
        """Test that should_cancel returns True when chained order price is reached (trigger_above=True)"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_price = decimal.Decimal("110.0")
        filling_price = decimal.Decimal("100.0")
        
        # Mock get_potentially_outdated_price to return up-to-date price
        with mock.patch.object(
            order_util,
            'get_potentially_outdated_price',
            return_value=(current_price, True)
        ):
            # Create real order
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("105.0"),
            )
            
            # Create real chained order
            chained_order = personal_data.SellLimitOrder(trader_inst)
            chained_order.update(
                order_type=enums.TraderOrderType.SELL_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=filling_price,
            )
            
            # Chain the orders
            await chained_order.set_as_chained_order(order, False, {}, False)
            order.add_chained_order(chained_order)
            
            policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
            
            # current_price (110) > filling_price (100) and trigger_above=True, should cancel
            assert policy.should_cancel(order) is True

    async def test_should_cancel_when_chained_order_price_reached_trigger_below(self, trader_simulator):
        """Test that should_cancel returns True when chained order price is reached (trigger_above=False)"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_price = decimal.Decimal("90.0")
        filling_price = decimal.Decimal("100.0")
        
        # Mock get_potentially_outdated_price to return up-to-date price
        with mock.patch.object(
            order_util,
            'get_potentially_outdated_price',
            return_value=(current_price, True)
        ):
            # Create real order
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("95.0"),
            )
            
            # Create real chained order
            chained_order = personal_data.BuyLimitOrder(trader_inst)
            chained_order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=filling_price,
            )
            
            # Chain the orders
            await chained_order.set_as_chained_order(order, False, {}, False)
            order.add_chained_order(chained_order)
            
            policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
            
            # current_price (90) < filling_price (100) and trigger_above=False, should cancel
            assert policy.should_cancel(order) is True

    async def test_should_not_cancel_when_chained_order_price_not_reached(self, trader_simulator):
        """Test that should_cancel returns False when chained order price is not reached"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_price = decimal.Decimal("95.0")
        filling_price = decimal.Decimal("100.0")
        
        # Mock get_potentially_outdated_price to return up-to-date price
        with mock.patch.object(
            order_util,
            'get_potentially_outdated_price',
            return_value=(current_price, True)
        ):
            # Create real order
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("95.0"),
            )
            
            # Create real chained order
            chained_order = personal_data.SellLimitOrder(trader_inst)
            chained_order.update(
                order_type=enums.TraderOrderType.SELL_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=filling_price,  # Need price > 100, but current is 95
            )
            
            # Chain the orders
            await chained_order.set_as_chained_order(order, False, {}, False)
            order.add_chained_order(chained_order)
            
            policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
            
            # current_price (95) < filling_price (100) and trigger_above=True, should not cancel
            assert policy.should_cancel(order) is False

    async def test_should_not_cancel_when_order_cleared(self, trader_simulator):
        """Test that should_cancel returns False when order is cleared"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        # Create real order and clear it
        order = personal_data.BuyLimitOrder(trader_inst)
        order.update(
            order_type=enums.TraderOrderType.BUY_LIMIT,
            symbol="BTC/USDT",
            current_price=decimal.Decimal("100.0"),
            quantity=decimal.Decimal("1.0"),
            price=decimal.Decimal("100.0"),
        )
        order.clear()
        
        policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
        
        logger_mock = mock.Mock(error=mock.Mock())
        with mock.patch.object(policy, "get_logger", mock.Mock(return_value=logger_mock)):
            assert policy.should_cancel(order) is False
            # Verify error was logged
            logger_mock.error.assert_called_once()

    async def test_should_not_cancel_when_no_chained_orders(self, trader_simulator):
        """Test that should_cancel returns False when order has no chained orders"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        # Create real order with no chained orders
        order = personal_data.BuyLimitOrder(trader_inst)
        order.update(
            order_type=enums.TraderOrderType.BUY_LIMIT,
            symbol="BTC/USDT",
            current_price=decimal.Decimal("100.0"),
            quantity=decimal.Decimal("1.0"),
            price=decimal.Decimal("100.0"),
        )
        # No chained orders added
        
        policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
        
        logger_mock = mock.Mock(error=mock.Mock())
        with mock.patch.object(policy, "get_logger", mock.Mock(return_value=logger_mock)):
            assert policy.should_cancel(order) is False
            # Verify error was logged
            logger_mock.error.assert_called_once()

    async def test_should_not_cancel_when_price_outdated(self, trader_simulator):
        """Test that should_cancel returns False when price is outdated"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_price = decimal.Decimal("110.0")
        filling_price = decimal.Decimal("100.0")
        
        # Mock get_potentially_outdated_price to return outdated price
        with mock.patch.object(
            order_util,
            'get_potentially_outdated_price',
            return_value=(current_price, False)  # up_to_date=False
        ):
            # Create real order
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("105.0"),
            )
            
            # Create real chained order
            chained_order = personal_data.SellLimitOrder(trader_inst)
            chained_order.update(
                order_type=enums.TraderOrderType.SELL_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=filling_price,
            )
            
            # Chain the orders
            await chained_order.set_as_chained_order(order, False, {}, False)
            order.add_chained_order(chained_order)
            
            policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
            
            logger_mock = mock.Mock(error=mock.Mock())
            with mock.patch.object(policy, "get_logger", mock.Mock(return_value=logger_mock)):
                assert policy.should_cancel(order) is False
                # Verify error was logged
                logger_mock.error.assert_called_once()

    async def test_should_cancel_with_multiple_chained_orders_when_one_reached(self, trader_simulator):
        """Test that should_cancel returns True when at least one chained order price is reached"""
        config, exchange_manager_inst, trader_inst = trader_simulator
        
        current_price = decimal.Decimal("110.0")
        
        # Mock get_potentially_outdated_price to return up-to-date price
        with mock.patch.object(
            order_util,
            'get_potentially_outdated_price',
            return_value=(current_price, True)
        ):
            # Create real order
            order = personal_data.BuyLimitOrder(trader_inst)
            order.update(
                order_type=enums.TraderOrderType.BUY_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("105.0"),
            )
            
            # Create real chained order 1 (not reached)
            chained_order_1 = personal_data.SellLimitOrder(trader_inst)
            chained_order_1.update(
                order_type=enums.TraderOrderType.SELL_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("120.0"),  # Not reached
            )
            
            # Create real chained order 2 (reached)
            chained_order_2 = personal_data.SellLimitOrder(trader_inst)
            chained_order_2.update(
                order_type=enums.TraderOrderType.SELL_LIMIT,
                symbol="BTC/USDT",
                current_price=current_price,
                quantity=decimal.Decimal("1.0"),
                price=decimal.Decimal("100.0"),  # Reached
            )
            
            # Chain the orders
            await chained_order_1.set_as_chained_order(order, False, {}, False)
            await chained_order_2.set_as_chained_order(order, False, {}, False)
            order.add_chained_order(chained_order_1)
            order.add_chained_order(chained_order_2)
            
            policy = chained_order_filling_price_order_cancel_policy_import.ChainedOrderFillingPriceOrderCancelPolicy()
            
            # One chained order price is reached, should cancel
            assert policy.should_cancel(order) is True
