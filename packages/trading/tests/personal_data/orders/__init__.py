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
import pytest_asyncio
import octobot_commons.symbols

# avoid circular imports when launching tests from this folder
import octobot_trading.api  # TODO fix circular import when importing octobot_trading.exchange_data first


from octobot_trading.enums import TradeOrderSide, TraderOrderType
from octobot_trading.personal_data.orders.types import BuyLimitOrder, SellLimitOrder, SellMarketOrder, BuyMarketOrder, \
    StopLossOrder, StopLossLimitOrder, TakeProfitOrder, TakeProfitLimitOrder, TrailingStopOrder, TrailingStopLimitOrder
from octobot_trading.personal_data.orders import Order


@pytest_asyncio.fixture()
async def order(trader):
    config, trader_inst, exchange_manager = trader
    return config, trader_inst, exchange_manager, Order(trader_inst)


@pytest_asyncio.fixture()
async def order_simulator(trader_simulator):
    config, trader_inst, exchange_manager = trader_simulator
    return config, trader_inst, exchange_manager, Order(trader_inst)


def created_order(order_type, order_type_enum, *args, **kwargs):
    order = order_type(*args, **kwargs)
    order.order_type = order_type_enum
    order.symbol = "BTC/USDT"
    order.currency, order.market = octobot_commons.symbols.parse_symbol(order.symbol).base_and_quote()
    return order



@pytest.fixture()
def backtesting_buy_and_sell_limit_orders(event_loop, backtesting_trader):
    _, _, trader_instance = backtesting_trader
    return (
        created_order(BuyLimitOrder, TraderOrderType.BUY_LIMIT, trader_instance),
        created_order(SellLimitOrder, TraderOrderType.SELL_LIMIT, trader_instance)
    )


@pytest.fixture()
def buy_limit_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(BuyLimitOrder, TraderOrderType.BUY_LIMIT, trader_instance)


@pytest.fixture()
def sell_limit_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(SellLimitOrder, TraderOrderType.SELL_LIMIT, trader_instance)


@pytest.fixture()
def buy_market_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(BuyMarketOrder, TraderOrderType.BUY_MARKET, trader_instance)


@pytest.fixture()
def sell_market_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(SellMarketOrder, TraderOrderType.SELL_MARKET, trader_instance)


@pytest.fixture()
def stop_loss_sell_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(StopLossOrder, TraderOrderType.STOP_LOSS, trader_instance, side=TradeOrderSide.SELL)


@pytest.fixture()
def stop_loss_buy_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(StopLossOrder, TraderOrderType.STOP_LOSS, trader_instance, side=TradeOrderSide.BUY)


@pytest.fixture()
def stop_loss_limit_order(event_loop, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    return created_order(StopLossLimitOrder, TraderOrderType.STOP_LOSS_LIMIT, trader_instance)


@pytest.fixture()
def take_profit_sell_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(TakeProfitOrder, TraderOrderType.TAKE_PROFIT, trader_instance, side=TradeOrderSide.SELL)


@pytest.fixture()
def take_profit_buy_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(TakeProfitOrder, TraderOrderType.TAKE_PROFIT, trader_instance, side=TradeOrderSide.BUY)


@pytest.fixture()
def take_profit_limit_order(event_loop, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    return created_order(TakeProfitLimitOrder, TraderOrderType.TAKE_PROFIT_LIMIT, trader_instance)


@pytest.fixture()
def trailing_stop_order(event_loop, simulated_trader):
    _, _, trader_instance = simulated_trader
    return created_order(TrailingStopOrder, TraderOrderType.TRAILING_STOP, trader_instance)


@pytest.fixture()
def trailing_stop_limit_order(event_loop, simulated_trader):
    _, exchange_manager, trader_instance = simulated_trader
    return created_order(TrailingStopLimitOrder, TraderOrderType.TRAILING_STOP_LIMIT, trader_instance)
