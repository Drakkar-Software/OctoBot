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
import math

from octobot_commons.constants import PORTFOLIO_TOTAL, PORTFOLIO_AVAILABLE
from octobot_trading.api.orders import get_open_orders
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc, TradeOrderSide, EvaluatorStates, \
    OrderStatus, TraderOrderType
from octobot_trading.orders.types import SellMarketOrder, BuyMarketOrder, SellLimitOrder, BuyLimitOrder


def check_order_limits(order, market_status):
    symbol_market_limits = market_status[Ecmsc.LIMITS.value]
    limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
    limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
    limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]

    min_quantity = limit_amount[Ecmsc.LIMITS_AMOUNT_MIN.value]
    max_quantity = limit_amount[Ecmsc.LIMITS_AMOUNT_MAX.value]
    min_cost = limit_cost[Ecmsc.LIMITS_COST_MIN.value]
    max_cost = limit_cost[Ecmsc.LIMITS_COST_MAX.value]
    min_price = limit_price[Ecmsc.LIMITS_PRICE_MIN.value]
    max_price = limit_price[Ecmsc.LIMITS_PRICE_MAX.value]
    maximal_price_digits = market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_PRICE.value]
    maximal_volume_digits = market_status[Ecmsc.PRECISION.value][Ecmsc.PRECISION_AMOUNT.value]
    order_cost = order.origin_price*order.origin_quantity

    assert order_cost <= max_cost
    assert order_cost >= min_cost
    assert order.origin_price <= max_price
    assert order.origin_price >= min_price
    assert str(order.origin_price)[::-1].find(".") <= maximal_price_digits
    assert order.origin_quantity <= max_quantity
    assert order.origin_quantity >= min_quantity
    assert str(order.origin_quantity)[::-1].find(".") <= maximal_volume_digits


def check_linked_order(order, linked_order, order_type, order_price, market_status):
    assert linked_order.exchange_manager == order.exchange_manager
    assert linked_order.trader == order.trader
    assert linked_order.order_type == order_type
    assert linked_order.created_last_price == order.created_last_price
    assert linked_order.origin_price == order_price
    assert linked_order.linked_orders[0] == order
    assert linked_order.created_last_price == order.created_last_price
    assert linked_order.currency == order.currency
    assert linked_order.fee == order.fee
    assert linked_order.filled_price == order.filled_price
    assert linked_order.filled_quantity == order.filled_quantity
    assert linked_order.linked_to == order
    assert linked_order.status == order.status
    assert linked_order.symbol == order.symbol
    check_order_limits(order, market_status)


def check_orders(orders, evaluation, state, nb_orders, market_status):

    if state == EvaluatorStates.NEUTRAL.value or state is None:
        assert orders == []
    else:
        if math.isnan(evaluation):
            assert orders == []
        elif state is None or isinstance(state, (int, float, dict)) or state not in [s.value for s in EvaluatorStates]:
            assert orders == []
        else:
            assert (not orders and nb_orders == 0) or (len(orders) == nb_orders) \
                or ((len(orders) == 0 or len(orders) == 1) and nb_orders == "unknown")
            if orders:
                order = orders[0]
                assert order.status == OrderStatus.OPEN
                assert order.simulated is True
                assert order.linked_to is None
                assert order.fee is None
                assert order.filled_price == 0
                assert order.filled_quantity == order.origin_quantity

                if state == EvaluatorStates.VERY_SHORT.value:
                    assert isinstance(order, SellMarketOrder)
                    assert order.side == TradeOrderSide.SELL
                    assert order.order_type == TraderOrderType.SELL_MARKET
                elif state == EvaluatorStates.SHORT.value:
                    assert isinstance(order, SellLimitOrder)
                    assert order.side == TradeOrderSide.SELL
                    assert order.order_type == TraderOrderType.SELL_LIMIT
                elif state == EvaluatorStates.VERY_LONG.value:
                    assert isinstance(order, BuyMarketOrder)
                    assert order.side == TradeOrderSide.BUY
                    assert order.order_type == TraderOrderType.BUY_MARKET
                elif state == EvaluatorStates.LONG.value:
                    assert isinstance(order, BuyLimitOrder)
                    assert order.side == TradeOrderSide.BUY
                    assert order.order_type == TraderOrderType.BUY_LIMIT

                check_order_limits(order, market_status)


def check_portfolio(portfolio, initial_portfolio, orders, only_positivity=False):
    if orders:
        orders_market_amount = 0
        orders_currency_amount = 0
        market = orders[0].market
        order_symbol = orders[0].currency
        for order in orders:
            assert order.market == market
            assert order.currency == order_symbol
            if order.side == TradeOrderSide.BUY:
                orders_market_amount += order.origin_quantity * order.origin_price
            else:
                orders_currency_amount += order.origin_quantity
            for symbol in portfolio:
                assert portfolio[symbol][PORTFOLIO_TOTAL] >= 0
                assert portfolio[symbol][PORTFOLIO_AVAILABLE] >= 0
                if not only_positivity:
                    if order_symbol == symbol:
                        assert initial_portfolio[symbol][PORTFOLIO_TOTAL] == portfolio[symbol][
                            PORTFOLIO_TOTAL]
                        assert "{:f}".format(
                            initial_portfolio[symbol][PORTFOLIO_AVAILABLE] - orders_currency_amount) == \
                            "{:f}".format(portfolio[symbol][PORTFOLIO_AVAILABLE])
                    elif market == symbol:
                        assert initial_portfolio[market][PORTFOLIO_TOTAL] == portfolio[market][
                            PORTFOLIO_TOTAL]
                        assert "{:f}".format(initial_portfolio[market][PORTFOLIO_AVAILABLE] - orders_market_amount) \
                               == "{:f}".format(portfolio[market][PORTFOLIO_AVAILABLE])


async def fill_orders(orders, trader):
    if orders:
        assert get_open_orders(trader.exchange_manager)
        for order in orders:
            order.filled_price = order.origin_price
            order.filled_quantity = order.origin_quantity
            await trader.notify_order_close(order)
            check_portfolio(trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio,
                            None, orders, True)
        assert len(get_open_orders(trader.exchange_manager)) == 0
