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
import octobot_trading.constants as trading_constants
from tests.personal_data import DEFAULT_ORDER_SYMBOL, DEFAULT_SYMBOL_QUANTITY
from tests.test_utils.random_numbers import decimal_random_price, decimal_random_quantity, \
    decimal_random_recent_trade

from tests import event_loop
from tests.exchanges import simulated_trader, simulated_exchange_manager
from tests.personal_data.orders import stop_loss_sell_order, stop_loss_buy_order

pytestmark = pytest.mark.asyncio


async def test_stop_loss_sell_order_trigger(stop_loss_sell_order):
    order_price = decimal_random_price()
    stop_loss_sell_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.STOP_LOSS,

    )
    stop_loss_sell_order.exchange_manager.is_backtesting = True  # force update_order_status
    await stop_loss_sell_order.initialize()
    await stop_loss_sell_order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
        stop_loss_sell_order
    )
    price_events_manager = stop_loss_sell_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    # stop loss sell order triggers when price is bellow or equal to its trigger price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(min_value=order_price + trading_constants.ONE),
                                     timestamp=stop_loss_sell_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not stop_loss_sell_order.is_filled()
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=order_price,
                                     timestamp=stop_loss_sell_order.timestamp - 1)])
    await wait_asyncio_next_cycle()
    assert not stop_loss_sell_order.is_filled()
    price_events_manager.handle_recent_trades([decimal_random_recent_trade(price=order_price,
                                                                           timestamp=stop_loss_sell_order.timestamp)])

    await wait_asyncio_next_cycle()
    assert stop_loss_sell_order.is_filled()


async def test_stop_loss_buy_order_trigger(stop_loss_buy_order):
    order_price = decimal_random_price()
    stop_loss_buy_order.update(
        price=order_price,
        quantity=decimal_random_quantity(max_value=DEFAULT_SYMBOL_QUANTITY),
        symbol=DEFAULT_ORDER_SYMBOL,
        order_type=TraderOrderType.STOP_LOSS,
    )
    stop_loss_buy_order.exchange_manager.is_backtesting = True  # force update_order_status
    await stop_loss_buy_order.initialize()
    await stop_loss_buy_order.exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(
        stop_loss_buy_order
    )
    price_events_manager = stop_loss_buy_order.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        DEFAULT_ORDER_SYMBOL).price_events_manager
    # stop loss buy order triggers when price is above or equal to its trigger price
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=decimal_random_price(max_value=order_price - trading_constants.ONE),
                                     timestamp=stop_loss_buy_order.timestamp)])
    await wait_asyncio_next_cycle()
    assert not stop_loss_buy_order.is_filled()
    price_events_manager.handle_recent_trades(
        [decimal_random_recent_trade(price=order_price,
                                     timestamp=stop_loss_buy_order.timestamp - 1)])
    await wait_asyncio_next_cycle()
    assert not stop_loss_buy_order.is_filled()
    price_events_manager.handle_recent_trades([decimal_random_recent_trade(price=order_price,
                                                                           timestamp=stop_loss_buy_order.timestamp)])

    await wait_asyncio_next_cycle()
    assert stop_loss_buy_order.is_filled()

    # TODO add test create artificial order
