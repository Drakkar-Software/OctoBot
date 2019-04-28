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

from abc import *
from copy import deepcopy
import math

from config import CURRENCY_DEFAULT_MAX_PRICE_DIGITS, ORDER_CREATION_LAST_TRADES_TO_USE, EvaluatorStates
from config import ExchangeConstantsMarketStatusColumns as Ecmsc
from tools.logging.logging_util import get_logger
from tools.symbol_util import split_symbol
from tools.dict_util import get_value_or_default
from tools.initializable import Initializable
from trading.trader.portfolio import Portfolio
from trading.trader.sub_portfolio import SubPortfolio
from trading.exchanges.exchange_market_status_fixer import ExchangeMarketStatusFixer


class AbstractTradingModeCreator:
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode):
        self.trading_mode = trading_mode

        self.logger = self.get_current_logger()

    @classmethod
    def get_current_logger(cls):
        return get_logger(cls.__name__)

    @staticmethod
    def check_factor(min_val, max_val, factor):
        if factor > max_val:
            return max_val
        elif factor < min_val:
            return min_val
        else:
            return factor

    @staticmethod
    def _is_valid(element, key):
        return key in element and ExchangeMarketStatusFixer.is_ms_valid(element[key])

    @staticmethod
    def add_dusts_to_quantity_if_necessary(quantity, price, symbol_market, current_symbol_holding):
        remaining_portfolio_amount = float("{1:.{0}f}".format(CURRENCY_DEFAULT_MAX_PRICE_DIGITS,
                                                              current_symbol_holding - quantity))
        remaining_max_total_order_price = remaining_portfolio_amount * price

        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
        limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]

        if not (AbstractTradingModeCreator._is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value) and
                AbstractTradingModeCreator._is_valid(limit_cost, Ecmsc.LIMITS_COST_MIN.value)):
            fixed_market_status = ExchangeMarketStatusFixer(symbol_market, price).get_market_status()
            limit_amount = fixed_market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_AMOUNT.value]
            limit_cost = fixed_market_status[Ecmsc.LIMITS.value][Ecmsc.LIMITS_COST.value]

        min_quantity = get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value, math.nan)
        min_cost = get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value, math.nan)

        # check with 40% more than remaining total not to require huge market moves to sell this asset
        min_cost_to_consider = min_cost * 1.4
        min_quantity_to_consider = min_quantity * 1.4

        if remaining_max_total_order_price < min_cost_to_consider \
                or remaining_portfolio_amount < min_quantity_to_consider:
            return current_symbol_holding
        else:
            return quantity

    """
    Checks and adapts the quantity and price of the order to ensure it's exchange compliant:
    - are the quantity and price of the order compliant with the exchange's number of digits requirement
        => otherwise quantity will be truncated accordingly
    - is the quantity valid
    - are the order total price and quantity superior or equal to the exchange's minimum order requirement
        => otherwise order is impossible => returns empty list
    - if total cost data are unavailable: 
    - is the price of the currency compliant with the exchange's price interval for this currency
        => otherwise order is impossible => returns empty list
    - are the order total price and quantity inferior or equal to the exchange's maximum order requirement
        => otherwise order is impossible as is => split order into smaller ones and returns the list
    => returns the quantity and price list of possible order(s)
    - if exchange symbol data are not enough
        => try fixing exchange data using ExchangeMarketStatusFixer are start again (once only)
    """

    @staticmethod
    def _check_cost(total_order_price, min_cost):
        if total_order_price < min_cost:
            if min_cost is None:
                AbstractTradingModeCreator.get_current_logger().error("Invalid min_cost from exchange")
            return False
        return True

    @staticmethod
    def _split_orders(total_order_price, max_cost, valid_quantity, max_quantity, price, quantity, symbol_market):
        if max_cost is None and max_quantity is None:
            raise RuntimeError("Impossible to split orders with max_cost and max_quantity undefined.")
        nb_orders_according_to_cost = None
        nb_orders_according_to_quantity = None
        if max_cost:
            nb_orders_according_to_cost = total_order_price / max_cost
        if max_quantity:
            nb_orders_according_to_quantity = valid_quantity / max_quantity
        if nb_orders_according_to_cost is None:
            # can only split using quantity
            return AbstractTradingModeCreator \
                ._adapt_order_quantity_because_quantity(valid_quantity, max_quantity,
                                                        quantity, price, symbol_market)
        elif nb_orders_according_to_quantity is None:
            # can only split using price
            return AbstractTradingModeCreator._adapt_order_quantity_because_price(total_order_price,
                                                                                  max_cost, price,
                                                                                  symbol_market)
        else:
            if nb_orders_according_to_cost > nb_orders_according_to_quantity:
                return AbstractTradingModeCreator._adapt_order_quantity_because_price(total_order_price,
                                                                                      max_cost, price,
                                                                                      symbol_market)
            else:
                return AbstractTradingModeCreator \
                    ._adapt_order_quantity_because_quantity(valid_quantity, max_quantity,
                                                            quantity, price, symbol_market)

    @staticmethod
    def get_min_max_amounts(symbol_market, default_value=None):
        min_quantity = max_quantity = min_cost = max_cost = min_price = max_price = default_value
        if Ecmsc.LIMITS.value in symbol_market:
            symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

            if Ecmsc.LIMITS_AMOUNT.value in symbol_market_limits:
                limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
                if AbstractTradingModeCreator._is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value) \
                        or AbstractTradingModeCreator._is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value):
                    min_quantity = get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value, default_value)
                    max_quantity = get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value, default_value)

            # case 2: use cost and price
            if Ecmsc.LIMITS_COST.value in symbol_market_limits:
                limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
                if AbstractTradingModeCreator._is_valid(limit_cost, Ecmsc.LIMITS_COST_MIN.value) \
                        or AbstractTradingModeCreator._is_valid(limit_cost, Ecmsc.LIMITS_COST_MAX.value):

                    min_cost = get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value, default_value)
                    max_cost = get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MAX.value, default_value)

            # case 2: use quantity and price
            if Ecmsc.LIMITS_PRICE.value in symbol_market_limits:
                limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]
                if AbstractTradingModeCreator._is_valid(limit_price, Ecmsc.LIMITS_PRICE_MIN.value) \
                        or AbstractTradingModeCreator._is_valid(limit_price, Ecmsc.LIMITS_PRICE_MAX.value):

                    min_price = get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MIN.value, default_value)
                    max_price = get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MAX.value, default_value)

        return min_quantity, max_quantity, min_cost, max_cost, min_price, max_price

    @staticmethod
    def check_and_adapt_order_details_if_necessary(quantity, price, symbol_market, fixed_symbol_data=False):
        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
        limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
        limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]

        # case 1: try with data directly from exchange
        if AbstractTradingModeCreator._is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value):
            min_quantity = get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value, math.nan)
            max_quantity = None
            # not all symbol data have a max quantity
            if AbstractTradingModeCreator._is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value):
                max_quantity = get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value, math.nan)

            # adapt digits if necessary
            valid_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, quantity)
            valid_price = AbstractTradingModeCreator.adapt_price(symbol_market, price)

            total_order_price = valid_quantity * valid_price

            if valid_quantity < min_quantity:
                # invalid order
                return []

            # case 1.1: use only quantity and cost
            if AbstractTradingModeCreator._is_valid(limit_cost, Ecmsc.LIMITS_COST_MIN.value):
                min_cost = get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value, math.nan)
                max_cost = None
                # not all symbol data have a max cost
                if AbstractTradingModeCreator._is_valid(limit_cost, Ecmsc.LIMITS_COST_MAX.value):
                    max_cost = get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MAX.value, math.nan)

                # check total_order_price not < min_cost
                if not AbstractTradingModeCreator._check_cost(total_order_price, min_cost):
                    return []

                # check total_order_price not > max_cost and valid_quantity not > max_quantity
                elif (max_cost is not None and total_order_price > max_cost) or \
                        (max_quantity is not None and valid_quantity > max_quantity):
                    # split quantity into smaller orders
                    return AbstractTradingModeCreator._split_orders(total_order_price, max_cost, valid_quantity,
                                                                    max_quantity, price, quantity, symbol_market)

                else:
                    # valid order that can be handled wy the exchange
                    return [(valid_quantity, valid_price)]

            # case 1.2: use only quantity and price
            elif AbstractTradingModeCreator._is_valid(limit_price, Ecmsc.LIMITS_PRICE_MIN.value):
                min_price = get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MIN.value, math.nan)
                max_price = None
                # not all symbol data have a max price
                if AbstractTradingModeCreator._is_valid(limit_price, Ecmsc.LIMITS_PRICE_MAX.value):
                    max_price = get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MAX.value, math.nan)

                if (max_price is not None and (max_price <= valid_price)) or valid_price <= min_price:
                    # invalid order
                    return []

                # check total_order_price not > max_cost and valid_quantity not > max_quantity
                elif max_quantity is not None and valid_quantity > max_quantity:
                    # split quantity into smaller orders
                    return AbstractTradingModeCreator \
                        ._adapt_order_quantity_because_quantity(valid_quantity, max_quantity,
                                                                quantity, price, symbol_market)
                else:
                    # valid order that can be handled wy the exchange
                    return [(valid_quantity, valid_price)]

        if not fixed_symbol_data:
            # case 2: try fixing data from exchanges
            fixed_data = ExchangeMarketStatusFixer(symbol_market, price).get_market_status()
            return AbstractTradingModeCreator.check_and_adapt_order_details_if_necessary(quantity, price, fixed_data,
                                                                                         fixed_symbol_data=True)
        else:
            # impossible to check if order is valid: refuse it
            return []

    @staticmethod
    async def get_holdings_ratio(trader, portfolio, currency):
        pf_copy = deepcopy(portfolio.get_portfolio())
        pf_value = await trader.get_trades_manager().update_portfolio_current_value(pf_copy)
        currency_holdings = Portfolio.get_currency_from_given_portfolio(pf_copy, currency,
                                                                        portfolio_type=Portfolio.TOTAL)
        currency_value = await trader.get_trades_manager().evaluate_value(currency, currency_holdings)
        return currency_value / pf_value if pf_value else 0

    @staticmethod
    def get_number_of_traded_assets(trader):
        return len(trader.get_trades_manager().origin_crypto_currencies_values)

    @staticmethod
    # Can be overwritten
    async def can_create_order(symbol, exchange, state, portfolio):
        currency, market = split_symbol(symbol)

        # get symbol min amount when creating order
        symbol_limit = exchange.get_market_status(symbol)[Ecmsc.LIMITS.value]
        symbol_min_amount = symbol_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]
        order_min_amount = symbol_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]

        if symbol_min_amount is None:
            symbol_min_amount = 0

        # short cases => sell => need this currency
        if state == EvaluatorStates.VERY_SHORT or state == EvaluatorStates.SHORT:
            return portfolio.get_currency_portfolio(currency) > symbol_min_amount

        # long cases => buy => need money(aka other currency in the pair) to buy this currency
        elif state == EvaluatorStates.LONG or state == EvaluatorStates.VERY_LONG:
            return portfolio.get_currency_portfolio(market) > order_min_amount

        # other cases like neutral state or unfulfilled previous conditions
        return False

    @staticmethod
    async def get_pre_order_data(exchange, symbol, portfolio):
        last_prices = await exchange.execute_request_with_retry(exchange.get_recent_trades(symbol))

        used_last_prices = last_prices[-ORDER_CREATION_LAST_TRADES_TO_USE:]

        reference_sum = sum([float(last_price["price"]) for last_price in used_last_prices])

        reference = reference_sum / len(used_last_prices)

        currency, market = split_symbol(symbol)

        current_symbol_holding = portfolio.get_currency_portfolio(currency)
        current_market_quantity = portfolio.get_currency_portfolio(market)

        market_quantity = current_market_quantity / reference

        price = reference
        symbol_market = exchange.get_market_status(symbol, with_fixer=False)

        return current_symbol_holding, current_market_quantity, market_quantity, price, symbol_market

    @abstractmethod
    def create_new_order(self, eval_note, symbol, exchange, trader, portfolio, state):
        raise NotImplementedError("create_new_order not implemented")

    @staticmethod
    def adapt_price(symbol_market, price):
        maximal_price_digits = get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                    Ecmsc.PRECISION_PRICE.value,
                                                    CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(price, maximal_price_digits)

    @staticmethod
    def _adapt_quantity(symbol_market, quantity):
        maximal_volume_digits = get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                     Ecmsc.PRECISION_AMOUNT.value, 0)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(quantity, maximal_volume_digits)

    @staticmethod
    def _trunc_with_n_decimal_digits(value, digits):
        # force exact representation
        return float("{0:.{1}f}".format(math.trunc(value * 10 ** digits) / (10 ** digits), digits))

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


class AbstractTradingModeCreatorWithBot(AbstractTradingModeCreator, Initializable):
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode, trader, sub_portfolio_percent):
        AbstractTradingModeCreator.__init__(self, trading_mode)
        Initializable.__init__(self)
        self.trader = trader
        self.parent_portfolio = self.trader.get_portfolio()
        self.sub_portfolio = SubPortfolio(self.trading_mode.config, self.trader, self.parent_portfolio,
                                          sub_portfolio_percent)

    async def initialize_impl(self):
        await self.sub_portfolio.initialize()

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
    async def can_create_order(self, symbol, exchange, state, portfolio):
        return await super().can_create_order(symbol, exchange, state, self.get_portfolio())

    # force portfolio update
    def get_portfolio(self, force_update=False):
        if force_update:
            self.sub_portfolio.update_from_parent()
        return self.sub_portfolio
