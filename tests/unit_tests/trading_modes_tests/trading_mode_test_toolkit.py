#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import math

import octobot_commons.constants as commons_constants
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enum
import octobot_trading.constants as trading_constants
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


def check_oco_order_group(order, order_type, order_price, market_status):
    orders_from_group = [found_order
                         for found_order in order.order_group.get_group_open_orders()
                         if found_order is not order]
    assert len(orders_from_group) == 1
    other_order_from_oco_group = orders_from_group[0]
    assert other_order_from_oco_group.exchange_manager == order.exchange_manager
    assert other_order_from_oco_group.trader == order.trader
    assert other_order_from_oco_group.order_type == order_type
    assert other_order_from_oco_group.created_last_price == order.created_last_price
    assert other_order_from_oco_group.origin_price == order_price
    assert other_order_from_oco_group.order_group is order.order_group
    assert other_order_from_oco_group.created_last_price == order.created_last_price
    assert other_order_from_oco_group.currency == order.currency
    assert other_order_from_oco_group.fee == order.fee
    assert other_order_from_oco_group.filled_price == order.filled_price
    assert other_order_from_oco_group.filled_quantity == order.filled_quantity
    assert other_order_from_oco_group.status == order.status
    assert other_order_from_oco_group.symbol == order.symbol
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
                    assert order.fee
                    assert order.filled_price > trading_constants.ZERO
                    assert order.filled_quantity == order.origin_quantity
                else:
                    assert order.status == trading_enum.OrderStatus.OPEN
                    assert order.simulated is True
                    assert order.fee is None
                    assert order.filled_price == trading_constants.ZERO
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
        orders_market_amount = trading_constants.ZERO
        orders_currency_amount = trading_constants.ZERO
        market = orders[0].market
        order_symbol = orders[0].currency
        for order in orders:
            assert order.market == market
            assert order.currency == order_symbol
            if order.side == trading_enum.TradeOrderSide.BUY:
                orders_market_amount += order.origin_quantity * order.origin_price
            else:
                orders_currency_amount += order.origin_quantity
            for symbol in [market, order_symbol]:
                assert portfolio.get_currency_portfolio(symbol).total >= trading_constants.ZERO
                assert portfolio.get_currency_portfolio(symbol).available >= trading_constants.ZERO
                if not only_positivity:
                    if order.order_type in (
                    trading_enum.TraderOrderType.SELL_MARKET, trading_enum.TraderOrderType.BUY_MARKET) and \
                            symbol in [order.market, order.currency]:
                        # order is filled
                        assert initial_portfolio.get_currency_portfolio(symbol) != \
                               portfolio.get_currency_portfolio(symbol)
                    else:
                        if order_symbol == symbol:
                            assert initial_portfolio.get_currency_portfolio(symbol).total == \
                                   portfolio.get_currency_portfolio(symbol).total
                            assert initial_portfolio.get_currency_portfolio(symbol).available - orders_currency_amount \
                                   == portfolio.get_currency_portfolio(symbol).available
                        elif market == symbol:
                            assert initial_portfolio.get_currency_portfolio(market).total == \
                                   portfolio.get_currency_portfolio(market).total
                            assert initial_portfolio.get_currency_portfolio(market).available - orders_market_amount \
                                   == portfolio.get_currency_portfolio(market).available


async def fill_orders(orders, trader):
    if orders:
        assert trading_api.get_open_orders(trader.exchange_manager)
        for order in orders:
            order.filled_price = order.origin_price
            order.filled_quantity = order.origin_quantity
            await order.on_fill(force_fill=True)
            check_portfolio(trader.exchange_manager.exchange_personal_data.portfolio_manager.portfolio,
                            None, orders, True)
        assert len(trading_api.get_open_orders(trader.exchange_manager)) == 0
