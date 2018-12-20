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
from abc import *

from config import *
from config import ExchangeConstantsMarketStatusColumns as Ecmsc
from tools.symbol_util import split_symbol
from trading.trader.sub_portfolio import SubPortfolio


class AbstractTradingModeCreator:
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode):
        self.trading_mode = trading_mode

    @staticmethod
    def check_factor(min_val, max_val, factor):
        if factor > max_val:
            return max_val
        elif factor < min_val:
            return min_val
        else:
            return factor

    @staticmethod
    def get_additional_dusts_to_quantity_if_necessary(quantity, price, symbol_market, current_symbol_holding):
        remaining_portfolio_amount = float("{1:.{0}f}".format(CURRENCY_DEFAULT_MAX_PRICE_DIGITS,
                                                              current_symbol_holding - quantity))
        remaining_max_total_order_price = remaining_portfolio_amount * price

        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
        limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]

        min_quantity = AbstractTradingModeCreator.get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value)
        min_cost = AbstractTradingModeCreator.get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value)

        if remaining_max_total_order_price < min_cost or remaining_portfolio_amount < min_quantity:
            return remaining_portfolio_amount
        else:
            return 0

    """
    Checks and adapts the quantity and price of the order to ensure it's exchange compliant:
    - are the quantity and price of the order compliant with the exchange's number of digits requirement
        => otherwise quantity and price will be truncated accordingly
    - is the price of the currency compliant with the exchange's price interval for this currency
        => otherwise order is impossible => returns empty list
    - are the order total price and quantity superior or equal to the exchange's minimum order requirement
        => otherwise order is impossible => returns empty list
    - are the order total price and quantity inferior or equal to the exchange's maximum order requirement
        => otherwise order is impossible as is => split order into smaller ones and returns the list
    => returns the quantity and price list of possible order(s)
    """

    @staticmethod
    def check_and_adapt_order_details_if_necessary(quantity, price, symbol_market):
        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
        limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
        limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]

        min_quantity = AbstractTradingModeCreator.get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value)
        max_quantity = AbstractTradingModeCreator.get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value)
        min_cost = AbstractTradingModeCreator.get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value)
        max_cost = AbstractTradingModeCreator.get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MAX.value)
        min_price = AbstractTradingModeCreator.get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MIN.value)
        max_price = AbstractTradingModeCreator.get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MAX.value)

        # adapt digits if necessary
        valid_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, quantity)
        valid_price = AbstractTradingModeCreator.adapt_price(symbol_market, price)

        total_order_price = valid_quantity * valid_price

        # check total_order_price not < min_cost and valid_quantity not < min_quantity and max_price > price > min_price
        if total_order_price < min_cost or valid_quantity < min_quantity or not (max_price >= valid_price >= min_price):
            # invalid order
            return []

        # check total_order_price not > max_cost and valid_quantity not > max_quantity
        elif total_order_price > max_cost or valid_quantity > max_quantity:
            # split quantity into smaller orders
            nb_orders_according_to_cost = total_order_price / max_cost
            nb_orders_according_to_quantity = valid_quantity / max_quantity
            if nb_orders_according_to_cost > nb_orders_according_to_quantity:
                return AbstractTradingModeCreator._adapt_order_quantity_because_price(total_order_price, max_cost,
                                                                                      price,
                                                                                      symbol_market)
            else:
                return AbstractTradingModeCreator._adapt_order_quantity_because_quantity(valid_quantity, max_quantity,
                                                                                         quantity, price, symbol_market)

        else:
            # valid order that can be handled wy the exchange
            return [(valid_quantity, valid_price)]

    @staticmethod
    # Can be overwritten
    def can_create_order(symbol, exchange, state, portfolio):
        currency, market = split_symbol(symbol)

        # get symbol min amount when creating order
        symbol_limit = exchange.get_market_status(symbol)[Ecmsc.LIMITS.value]
        symbol_min_amount = symbol_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]
        order_min_amount = symbol_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]

        # short cases => sell => need this currency
        if state == EvaluatorStates.VERY_SHORT or state == EvaluatorStates.SHORT:
            return portfolio.get_currency_portfolio(currency) > symbol_min_amount

        # long cases => buy => need money(aka other currency in the pair) to buy this currency
        elif state == EvaluatorStates.LONG or state == EvaluatorStates.VERY_LONG:
            return portfolio.get_currency_portfolio(market) > order_min_amount

        # other cases like neutral state or unfulfilled previous conditions
        return False

    @staticmethod
    def get_pre_order_data(exchange, symbol, portfolio):
        last_prices = exchange.get_recent_trades(symbol)

        reference_sum = sum([float(last_price["price"])
                             for last_price in last_prices[-ORDER_CREATION_LAST_TRADES_TO_USE:]])

        reference = reference_sum / ORDER_CREATION_LAST_TRADES_TO_USE

        currency, market = split_symbol(symbol)

        current_symbol_holding = portfolio.get_currency_portfolio(currency)
        current_market_quantity = portfolio.get_currency_portfolio(market)

        market_quantity = current_market_quantity / reference

        price = reference
        symbol_market = exchange.get_market_status(symbol)

        return current_symbol_holding, current_market_quantity, market_quantity, price, symbol_market

    @abstractmethod
    def create_new_order(self, eval_note, symbol, exchange, trader, portfolio, state):
        raise NotImplementedError("create_new_order not implemented")

    @staticmethod
    def adapt_price(symbol_market, price):
        maximal_price_digits = AbstractTradingModeCreator.get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                               Ecmsc.PRECISION_PRICE.value,
                                                                               CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(price, maximal_price_digits)

    @staticmethod
    def _adapt_quantity(symbol_market, quantity):
        maximal_volume_digits = AbstractTradingModeCreator.get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                                Ecmsc.PRECISION_AMOUNT.value, 0)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(quantity, maximal_volume_digits)

    @staticmethod
    def _trunc_with_n_decimal_digits(value, digits):
        # force exact representation
        return float("{0:.{1}f}".format(math.trunc(value * 10 ** digits) / (10 ** digits), digits))

    @staticmethod
    def get_value_or_default(dictionary, key, default=math.nan):
        if key in dictionary:
            value = dictionary[key]
            return value if value is not None else default
        return default

    @staticmethod
    def _adapt_order_quantity_because_quantity(limiting_value, max_value, quantity_to_adapt, price, symbol_market):
        orders = []
        nb_full_orders = limiting_value // max_value
        rest_order_quantity = limiting_value % max_value
        after_rest_quantity_to_adapt = quantity_to_adapt

        if rest_order_quantity > 0:
            after_rest_quantity_to_adapt -= rest_order_quantity
            valid_last_order_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, rest_order_quantity)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = (after_rest_quantity_to_adapt + max_value) / (nb_full_orders + 1)
        valid_other_orders_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)] * int(nb_full_orders)
        return orders

    @staticmethod
    def _adapt_order_quantity_because_price(limiting_value, max_value, price, symbol_market):
        orders = []
        nb_full_orders = limiting_value // max_value
        rest_order_cost = limiting_value % max_value
        if rest_order_cost > 0:
            valid_last_order_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market,
                                                                                   rest_order_cost / price)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = max_value / price
        valid_other_orders_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)] * int(nb_full_orders)
        return orders


class AbstractTradingModeCreatorWithBot(AbstractTradingModeCreator):
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode, trader, sub_portfolio_percent):
        super().__init__(trading_mode)
        self.trader = trader
        self.parent_portfolio = self.trader.get_portfolio()
        self.sub_portfolio = SubPortfolio(self.trading_mode.config,
                                          self.trader,
                                          self.parent_portfolio,
                                          sub_portfolio_percent,
                                          is_relative=True)

    @abstractmethod
    def create_new_order(self, eval_note, symbol, exchange, trader, portfolio, state):
        raise NotImplementedError("create_new_order not implemented")

    def get_trader(self):
        return self.trader

    def get_parent_portfolio(self):
        return self.parent_portfolio

    def get_sub_portfolio(self):
        return self.sub_portfolio

    # Can be overwritten
    def can_create_order(self, symbol, exchange, state, portfolio):
        return super().can_create_order(symbol, exchange, state, self.get_portfolio())

    # force portfolio update
    def get_portfolio(self, force_update=False):
        if force_update:
            self.sub_portfolio.update_from_parent()
        return self.sub_portfolio
