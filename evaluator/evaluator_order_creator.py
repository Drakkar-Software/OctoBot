import logging
import math

from config.cst import *
from config.cst import ExchangeConstantsMarketStatusColumns as Ecmsc
from tools.symbol_util import split_symbol


class EvaluatorOrderCreator:
    def __init__(self):
        self.MAX_SUM_RESULT = 2

        self.STOP_LOSS_ORDER_MAX_PERCENT = 0.99
        self.STOP_LOSS_ORDER_MIN_PERCENT = 0.95
        self.STOP_LOSS_ORDER_ATTENUATION = (self.STOP_LOSS_ORDER_MAX_PERCENT - self.STOP_LOSS_ORDER_MIN_PERCENT)

        self.QUANTITY_MIN_PERCENT = 0.1
        self.QUANTITY_MAX_PERCENT = 0.9
        self.QUANTITY_ATTENUATION = (self.QUANTITY_MAX_PERCENT - self.QUANTITY_MIN_PERCENT) / self.MAX_SUM_RESULT

        self.QUANTITY_MARKET_MIN_PERCENT = 0.5
        self.QUANTITY_MARKET_MAX_PERCENT = 1
        self.QUANTITY_BUY_MARKET_ATTENUATION = 0.2
        self.QUANTITY_MARKET_ATTENUATION = (self.QUANTITY_MARKET_MAX_PERCENT - self.QUANTITY_MARKET_MIN_PERCENT) \
            / self.MAX_SUM_RESULT

        self.BUY_LIMIT_ORDER_MAX_PERCENT = 0.995
        self.BUY_LIMIT_ORDER_MIN_PERCENT = 0.98
        self.SELL_LIMIT_ORDER_MIN_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MAX_PERCENT)
        self.SELL_LIMIT_ORDER_MAX_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MIN_PERCENT)
        self.LIMIT_ORDER_ATTENUATION = (self.BUY_LIMIT_ORDER_MAX_PERCENT - self.BUY_LIMIT_ORDER_MIN_PERCENT)\
            / self.MAX_SUM_RESULT

    @staticmethod
    def can_create_order(symbol, exchange, trader, state):
        currency, market = split_symbol(symbol)
        portfolio = trader.get_portfolio()

        # get symbol min amount when creating order
        symbol_limit = exchange.get_market_status(symbol)[Ecmsc.LIMITS.value]
        symbol_min_amount = symbol_limit[Ecmsc.LIMITS_AMOUNT.value][Ecmsc.LIMITS_AMOUNT_MIN.value]
        order_min_amount = symbol_limit[Ecmsc.LIMITS_COST.value][Ecmsc.LIMITS_COST_MIN.value]

        # short cases => sell => need this currency
        if state == EvaluatorStates.VERY_SHORT or state == EvaluatorStates.SHORT:
            with portfolio as pf:
                return pf.get_currency_portfolio(currency) > symbol_min_amount

        # long cases => buy => need money(aka other currency in the pair) to buy this currency
        elif state == EvaluatorStates.LONG or state == EvaluatorStates.VERY_LONG:
            with portfolio as pf:
                return pf.get_currency_portfolio(market) > order_min_amount

        # other cases like neutral state or unfulfilled previous conditions
        return False

    # creates a new order (or multiple split orders), always check EvaluatorOrderCreator.can_create_order() first.
    def create_new_order(self, eval_note, symbol, exchange, trader, portfolio, state):
        try:
            last_prices = exchange.get_recent_trades(symbol)
            reference_sum = 0

            for last_price in last_prices[-ORDER_CREATION_LAST_TRADES_TO_USE:]:
                reference_sum += float(last_price["price"])

            reference = reference_sum / ORDER_CREATION_LAST_TRADES_TO_USE

            currency, market = split_symbol(symbol)

            current_portfolio = portfolio.get_currency_portfolio(currency)
            current_market_quantity = portfolio.get_currency_portfolio(market)

            market_quantity = current_market_quantity / reference

            price = reference
            symbol_market = exchange.get_market_status(symbol)

            created_orders = []
            # TODO : temp
            if state == EvaluatorStates.VERY_SHORT:
                quantity = self._get_market_quantity_from_risk(eval_note,
                                                               trader,
                                                               current_portfolio)
                for order_quantity, order_price in self._check_and_adapt_order_details_if_necessary(quantity, price,
                                                                                                    symbol_market):
                    market = trader.create_order_instance(order_type=TraderOrderType.SELL_MARKET,
                                                          symbol=symbol,
                                                          current_price=order_price,
                                                          quantity=order_quantity,
                                                          price=order_price)
                    trader.create_order(market, portfolio)
                    created_orders.append(market)
                return created_orders

            elif state == EvaluatorStates.SHORT:
                quantity = self._get_limit_quantity_from_risk(eval_note,
                                                              trader,
                                                              current_portfolio)
                limit_price = EvaluatorOrderCreator\
                    ._adapt_price(symbol_market, price * self._get_limit_price_from_risk(eval_note, trader))
                for order_quantity, order_price in self._check_and_adapt_order_details_if_necessary(quantity,
                                                                                                    limit_price,
                                                                                                    symbol_market):
                    limit = trader.create_order_instance(order_type=TraderOrderType.SELL_LIMIT,
                                                         symbol=symbol,
                                                         current_price=price,
                                                         quantity=order_quantity,
                                                         price=order_price)
                    trader.create_order(limit, portfolio)
                    created_orders.append(limit)

                    stop_price = EvaluatorOrderCreator\
                        ._adapt_price(symbol_market, price * self._get_stop_price_from_risk(trader))
                    stop = trader.create_order_instance(order_type=TraderOrderType.STOP_LOSS,
                                                        symbol=symbol,
                                                        current_price=price,
                                                        quantity=order_quantity,
                                                        price=stop_price,
                                                        linked_to=limit)
                    trader.create_order(stop, portfolio)
                return created_orders

            elif state == EvaluatorStates.NEUTRAL:
                pass

            # TODO : stop loss
            elif state == EvaluatorStates.LONG:
                quantity = self._get_limit_quantity_from_risk(eval_note,
                                                              trader,
                                                              market_quantity)
                limit_price = EvaluatorOrderCreator\
                    ._adapt_price(symbol_market, price * self._get_limit_price_from_risk(eval_note, trader))
                for order_quantity, order_price in self._check_and_adapt_order_details_if_necessary(quantity,
                                                                                                    limit_price,
                                                                                                    symbol_market):
                    limit = trader.create_order_instance(order_type=TraderOrderType.BUY_LIMIT,
                                                         symbol=symbol,
                                                         current_price=price,
                                                         quantity=order_quantity,
                                                         price=order_price)
                    trader.create_order(limit, portfolio)
                    created_orders.append(limit)
                return created_orders

            elif state == EvaluatorStates.VERY_LONG:
                quantity = self._get_market_quantity_from_risk(eval_note,
                                                               trader,
                                                               market_quantity,
                                                               True)
                for order_quantity, order_price in self._check_and_adapt_order_details_if_necessary(quantity, price,
                                                                                                    symbol_market):
                    market = trader.create_order_instance(order_type=TraderOrderType.BUY_MARKET,
                                                          symbol=symbol,
                                                          current_price=order_price,
                                                          quantity=order_quantity,
                                                          price=order_price)
                    trader.create_order(market, portfolio)
                    created_orders.append(market)
                return created_orders

        except Exception as e:
            logging.getLogger(self.__class__.__name__).error("Failed to create order : {0}".format(e))
            return None

    @staticmethod
    def _check_factor(min_val, max_val, factor):
        if factor > max_val:
            return max_val
        elif factor < min_val:
            return min_val
        else:
            return factor

    """
    Starting point : self.SELL_LIMIT_ORDER_MIN_PERCENT or self.BUY_LIMIT_ORDER_MAX_PERCENT
    1 - abs(eval_note) --> confirmation level --> high : sell less expensive / buy more expensive
    1 - trader.get_risk() --> high risk : sell / buy closer to the current price
    1 - abs(eval_note) + 1 - trader.get_risk() --> result between 0 and 2 --> self.MAX_SUM_RESULT
    self.QUANTITY_ATTENUATION --> try to contains the result between self.XXX_MIN_PERCENT and self.XXX_MAX_PERCENT
    """

    def _get_limit_price_from_risk(self, eval_note, trader):
        if eval_note > 0:
            factor = self.SELL_LIMIT_ORDER_MIN_PERCENT + \
                     ((1 - abs(eval_note) + 1 - trader.get_risk()) * self.LIMIT_ORDER_ATTENUATION)
            return EvaluatorOrderCreator._check_factor(self.SELL_LIMIT_ORDER_MIN_PERCENT,
                                                       self.SELL_LIMIT_ORDER_MAX_PERCENT,
                                                       factor)
        else:
            factor = self.BUY_LIMIT_ORDER_MAX_PERCENT - \
                     ((1 - abs(eval_note) + 1 - trader.get_risk()) * self.LIMIT_ORDER_ATTENUATION)
            return EvaluatorOrderCreator._check_factor(self.BUY_LIMIT_ORDER_MIN_PERCENT,
                                                       self.BUY_LIMIT_ORDER_MAX_PERCENT,
                                                       factor)

    """
    Starting point : self.STOP_LOSS_ORDER_MAX_PERCENT
    trader.get_risk() --> low risk : stop level close to the current price
    self.STOP_LOSS_ORDER_ATTENUATION --> try to contains the result between self.STOP_LOSS_ORDER_MIN_PERCENT and self.STOP_LOSS_ORDER_MAX_PERCENT
    """

    def _get_stop_price_from_risk(self, trader):
        factor = self.STOP_LOSS_ORDER_MAX_PERCENT - (trader.get_risk() * self.STOP_LOSS_ORDER_ATTENUATION)
        return EvaluatorOrderCreator._check_factor(self.STOP_LOSS_ORDER_MIN_PERCENT,
                                                   self.STOP_LOSS_ORDER_MAX_PERCENT,
                                                   factor)

    """
    Starting point : self.QUANTITY_MIN_PERCENT
    abs(eval_note) --> confirmation level --> high : sell/buy more quantity
    trader.get_risk() --> high risk : sell / buy more quantity
    abs(eval_note) + trader.get_risk() --> result between 0 and 2 --> self.MAX_SUM_RESULT
    self.QUANTITY_ATTENUATION --> try to contains the result between self.QUANTITY_MIN_PERCENT and self.QUANTITY_MAX_PERCENT
    """

    def _get_limit_quantity_from_risk(self, eval_note, trader, quantity):
        factor = self.QUANTITY_MIN_PERCENT + ((abs(eval_note) + trader.get_risk()) * self.QUANTITY_ATTENUATION)
        return EvaluatorOrderCreator._check_factor(self.QUANTITY_MIN_PERCENT,
                                                   self.QUANTITY_MAX_PERCENT,
                                                   factor) * quantity

    """
    Starting point : self.QUANTITY_MARKET_MIN_PERCENT
    abs(eval_note) --> confirmation level --> high : sell/buy more quantity
    trader.get_risk() --> high risk : sell / buy more quantity
    abs(eval_note) + trader.get_risk() --> result between 0 and 2 --> self.MAX_SUM_RESULT
    self.QUANTITY_MARKET_ATTENUATION --> try to contains the result between self.QUANTITY_MARKET_MIN_PERCENT and self.QUANTITY_MARKET_MAX_PERCENT
    """

    def _get_market_quantity_from_risk(self, eval_note, trader, quantity, buy=False):
        factor = self.QUANTITY_MARKET_MIN_PERCENT + (
                (abs(eval_note) + trader.get_risk()) * self.QUANTITY_MARKET_ATTENUATION)

        # if buy market --> limit market usage
        if buy:
            factor *= self.QUANTITY_BUY_MARKET_ATTENUATION

        return EvaluatorOrderCreator._check_factor(self.QUANTITY_MARKET_MIN_PERCENT,
                                                   self.QUANTITY_MARKET_MAX_PERCENT,
                                                   factor) * quantity

    @staticmethod
    def _trunc_with_n_decimal_digits(value, digits):
        return math.trunc(value*10**digits)/(10**digits)

    @staticmethod
    def _get_value_or_default(dictionary, key, default=math.nan):
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
            valid_last_order_quantity = EvaluatorOrderCreator._adapt_quantity(symbol_market, rest_order_quantity)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = (after_rest_quantity_to_adapt + max_value)/(nb_full_orders+1)
        valid_other_orders_quantity = EvaluatorOrderCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)]*int(nb_full_orders)
        return orders

    @staticmethod
    def _adapt_order_quantity_because_price(limiting_value, max_value, quantity_to_adapt, price, symbol_market):
        orders = []
        nb_full_orders = limiting_value // max_value
        rest_order_cost = limiting_value % max_value
        if rest_order_cost > 0:
            valid_last_order_quantity = EvaluatorOrderCreator._adapt_quantity(symbol_market, rest_order_cost/price)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = max_value / price
        valid_other_orders_quantity = EvaluatorOrderCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)] * int(nb_full_orders)
        return orders

    @staticmethod
    def _adapt_price(symbol_market, price):
        maximal_price_digits = EvaluatorOrderCreator._get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                           Ecmsc.PRECISION_PRICE.value,
                                                                           CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        return EvaluatorOrderCreator._trunc_with_n_decimal_digits(price, maximal_price_digits)

    @staticmethod
    def _adapt_quantity(symbol_market, quantity):
        maximal_volume_digits = EvaluatorOrderCreator._get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                            Ecmsc.PRECISION_AMOUNT.value, 0)
        return EvaluatorOrderCreator._trunc_with_n_decimal_digits(quantity, maximal_volume_digits)

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
    def _check_and_adapt_order_details_if_necessary(quantity, price, symbol_market):
        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
        limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
        limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]

        min_quantity = EvaluatorOrderCreator._get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value)
        max_quantity = EvaluatorOrderCreator._get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value)
        min_cost = EvaluatorOrderCreator._get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value)
        max_cost = EvaluatorOrderCreator._get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MAX.value)
        min_price = EvaluatorOrderCreator._get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MIN.value)
        max_price = EvaluatorOrderCreator._get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MAX.value)

        # adapt digits if necessary
        valid_quantity = EvaluatorOrderCreator._adapt_quantity(symbol_market, quantity)
        valid_price = EvaluatorOrderCreator._adapt_price(symbol_market, price)

        total_order_price = valid_quantity * valid_price

        # check total_order_price not < min_cost and valid_quantity not < min_quantity and max_price > price > min_price
        if total_order_price < min_cost or valid_quantity < min_quantity or not (max_price > valid_price > min_price):
            # invalid order
            return []

        # check total_order_price not > max_cost and valid_quantity not > max_quantity
        elif total_order_price > max_cost or valid_quantity > max_quantity:
            # split quantity into smaller orders
            nb_orders_according_to_cost = total_order_price / max_cost
            nb_orders_according_to_quantity = valid_quantity / max_quantity
            if nb_orders_according_to_cost > nb_orders_according_to_quantity:
                return EvaluatorOrderCreator._adapt_order_quantity_because_price(total_order_price, max_cost, quantity,
                                                                                 price, symbol_market)
            else:
                return EvaluatorOrderCreator._adapt_order_quantity_because_quantity(valid_quantity, max_quantity,
                                                                                    quantity, price, symbol_market)

        else:
            # valid order that can be handled wy the exchange
            return [(valid_quantity, valid_price)]
