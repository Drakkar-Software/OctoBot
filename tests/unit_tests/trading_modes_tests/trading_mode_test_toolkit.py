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

import octobot_commons.constants as commons_constants
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enum
import octobot_trading.personal_data as trading_personal_data


def check_order_limits(order, market_status):
    symbol_market_limits = market_status[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS.value]
    limit_amount = symbol_market_limits[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value]
    limit_cost = symbol_market_limits[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_COST.value]
    limit_price = symbol_market_limits[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value]

    min_quantity = limit_amount[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value]
    max_quantity = limit_amount[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value]
    min_cost = limit_cost[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value]
    max_cost = limit_cost[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value]
    min_price = limit_price[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value]
    max_price = limit_price[trading_enum.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value]
    maximal_price_digits = market_status[trading_enum.ExchangeConstantsMarketStatusColumns.PRECISION.value][
        trading_enum.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value]
    maximal_volume_digits = market_status[trading_enum.ExchangeConstantsMarketStatusColumns.PRECISION.value][
        trading_enum.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value]
    order_cost = order.origin_price * order.origin_quantity

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
    if state == trading_enum.EvaluatorStates.NEUTRAL.value or state is None:
        assert orders == []
    else:
        if math.isnan(evaluation):
            assert orders == []
        elif state is None or isinstance(state, (int, float, dict)) or state not in [s.value for s in
                                                                                     trading_enum.EvaluatorStates]:
            assert orders == []
        else:
            assert (not orders and nb_orders == 0) or (len(orders) == nb_orders) \
                   or ((len(orders) == 0 or len(orders) == 1) and nb_orders == "unknown")
            if orders:
                order = orders[0]
                if order.order_type in (
                trading_enum.TraderOrderType.SELL_MARKET, trading_enum.TraderOrderType.BUY_MARKET):
                    assert order.status == trading_enum.OrderStatus.FILLED
                    assert order.simulated is True
                    assert order.linked_to is None
                    assert order.fee
                    assert order.filled_price > 0
                    assert order.filled_quantity == order.origin_quantity
                else:
                    assert order.status == trading_enum.OrderStatus.OPEN
                    assert order.simulated is True
                    assert order.linked_to is None
                    assert order.fee is None
                    assert order.filled_price == 0
                    assert order.filled_quantity == order.origin_quantity

                if state == trading_enum.EvaluatorStates.VERY_SHORT.value:
                    assert isinstance(order, trading_personal_data.SellMarketOrder)
                    assert order.side == trading_enum.TradeOrderSide.SELL
                    assert order.order_type == trading_enum.TraderOrderType.SELL_MARKET
                elif state == trading_enum.EvaluatorStates.SHORT.value:
                    assert isinstance(order, trading_personal_data.SellLimitOrder)
                    assert order.side == trading_enum.TradeOrderSide.SELL
                    assert order.order_type == trading_enum.TraderOrderType.SELL_LIMIT
                elif state == trading_enum.EvaluatorStates.VERY_LONG.value:
                    assert isinstance(order, trading_personal_data.BuyMarketOrder)
                    assert order.side == trading_enum.TradeOrderSide.BUY
                    assert order.order_type == trading_enum.TraderOrderType.BUY_MARKET
                elif state == trading_enum.EvaluatorStates.LONG.value:
                    assert isinstance(order, trading_personal_data.BuyLimitOrder)
                    assert order.side == trading_enum.TradeOrderSide.BUY
                    assert order.order_type == trading_enum.TraderOrderType.BUY_LIMIT

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
            if order.side == trading_enum.TradeOrderSide.BUY:
                orders_market_amount += order.origin_quantity * order.origin_price
            else:
                orders_currency_amount += order.origin_quantity
            for symbol in portfolio:
                assert portfolio[symbol][commons_constants.PORTFOLIO_TOTAL] >= 0
                assert portfolio[symbol][commons_constants.PORTFOLIO_AVAILABLE] >= 0
                if not only_positivity:
                    if order.order_type in (
                    trading_enum.TraderOrderType.SELL_MARKET, trading_enum.TraderOrderType.BUY_MARKET):
                        # order is filled
                        assert initial_portfolio[symbol][commons_constants.PORTFOLIO_TOTAL] != portfolio[symbol][
                            commons_constants.PORTFOLIO_TOTAL]
                        assert initial_portfolio[symbol][commons_constants.PORTFOLIO_AVAILABLE] != portfolio[symbol][
                            commons_constants.PORTFOLIO_AVAILABLE]
                    else:
                        if order_symbol == symbol:
                            assert initial_portfolio[symbol][commons_constants.PORTFOLIO_TOTAL] == portfolio[symbol][
                                commons_constants.PORTFOLIO_TOTAL]
                            assert "{:f}".format(
                                initial_portfolio[symbol][
                                    commons_constants.PORTFOLIO_AVAILABLE] - orders_currency_amount) == \
                                   "{:f}".format(portfolio[symbol][commons_constants.PORTFOLIO_AVAILABLE])
                        elif market == symbol:
                            assert initial_portfolio[market][commons_constants.PORTFOLIO_TOTAL] == portfolio[market][
                                commons_constants.PORTFOLIO_TOTAL]
                            assert "{:f}".format(
                                initial_portfolio[market][commons_constants.PORTFOLIO_AVAILABLE] - orders_market_amount) \
                                   == "{:f}".format(portfolio[market][commons_constants.PORTFOLIO_AVAILABLE])


async def fill_orders(orders, trader):
    if orders:
        assert trading_api.get_open_orders(trader.exchange_manager)
        for order in orders:
            order.filled_price = order.origin_price
            order.filled_quantity = order.origin_quantity
            await order.on_fill(force_fill=True)
            check_portfolio(trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio,
                            None, orders, True)
        assert len(trading_api.get_open_orders(trader.exchange_manager)) == 0
