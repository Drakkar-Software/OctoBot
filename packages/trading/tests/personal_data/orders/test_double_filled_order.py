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

from octobot_commons.asyncio_tools import wait_asyncio_next_cycle
from octobot_trading.enums import TraderOrderType
from tests.personal_data import DEFAULT_SYMBOL_QUANTITY, DEFAULT_ORDER_SYMBOL
from tests.test_utils.random_numbers import decimal_random_price, random_price, decimal_random_quantity, \
    random_recent_trade
import octobot_trading.personal_data.orders.groups as order_groups

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import stop_loss_sell_order, sell_limit_order

pytestmark = pytest.mark.asyncio


async def test_stop_loss_and_limit(stop_loss_sell_order, sell_limit_order):
    # fill both orders: stop loss first
    limit_order_price = decimal_random_price()
    quantity = decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY)
    sell_limit_order.update(
        price=limit_order_price,
        quantity=quantity,
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.SELL_LIMIT,
    )
    stop_order_price = decimal_random_price(max_value=limit_order_price-1)
    stop_loss_sell_order.update(
        price=stop_order_price,
        quantity=quantity,
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.STOP_LOSS
    )
    oco_group = stop_loss_sell_order.exchange_manager.exchange_personal_data.orders_manager\
        .create_group(order_groups.OneCancelsTheOtherOrderGroup)
    stop_loss_sell_order.add_to_order_group(oco_group)
    sell_limit_order.add_to_order_group(oco_group)
    stop_loss_sell_order.exchange_manager.is_backtesting = True  # force update_order_status
    # initialize stop loss first
    await stop_loss_sell_order.initialize()
    await sell_limit_order.initialize()
    price_events_manager = stop_loss_sell_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    # stop loss sell order triggers when price is bellow or equal to its trigger price
    # sell limit order triggers when price is above or equal to its trigger price
    # here trigger both: stop order is triggered first (initialized first): sell limit order should be
    # cancelled and not filled even though its price has been hit
    price_events_manager.handle_recent_trades(
         [
            random_recent_trade(price=random_price(max_value=float(stop_order_price - 1)),
                                timestamp=stop_loss_sell_order.timestamp),
            random_recent_trade(price=random_price(min_value=float(limit_order_price + 1)),
                                timestamp=sell_limit_order.timestamp)
         ]
    )
    await wait_asyncio_next_cycle()
    assert stop_loss_sell_order.is_filled()
    assert sell_limit_order.is_cancelled()


async def test_limit_and_stop_loss(stop_loss_sell_order, sell_limit_order):
    # fill both orders: limit first
    limit_order_price = decimal_random_price()
    quantity = decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY)
    sell_limit_order.update(
        price=limit_order_price,
        quantity=quantity,
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.SELL_LIMIT,
    )
    stop_order_price = decimal_random_price(max_value=limit_order_price-1)
    stop_loss_sell_order.update(
        price=stop_order_price,
        quantity=quantity,
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.STOP_LOSS
    )
    oco_group = stop_loss_sell_order.exchange_manager.exchange_personal_data.orders_manager\
        .create_group(order_groups.OneCancelsTheOtherOrderGroup)
    stop_loss_sell_order.add_to_order_group(oco_group)
    sell_limit_order.add_to_order_group(oco_group)
    stop_loss_sell_order.exchange_manager.is_backtesting = True  # force update_order_status
    # initialize limit order first
    await sell_limit_order.initialize()
    await stop_loss_sell_order.initialize()
    price_events_manager = stop_loss_sell_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    # stop loss sell order triggers when price is bellow or equal to its trigger price
    # sell limit order triggers when price is above or equal to its trigger price
    # here trigger both: limit is triggered first (initialized first): sell stop loss order should be
    # cancelled and not filled even though its price has been hit
    price_events_manager.handle_recent_trades(
         [
            random_recent_trade(price=random_price(max_value=float(stop_order_price - 1)),
                                timestamp=sell_limit_order.timestamp),
            random_recent_trade(price=random_price(min_value=float(limit_order_price + 1)),
                                timestamp=stop_loss_sell_order.timestamp)
         ]
    )
    await wait_asyncio_next_cycle()
    assert stop_loss_sell_order.is_cancelled()
    assert sell_limit_order.is_filled()
