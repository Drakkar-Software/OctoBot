import math
from abc import *

from config.cst import *
from config.cst import ExchangeConstantsMarketStatusColumns as Ecmsc
from tools.symbol_util import split_symbol


class AbstractTradingModeCreator:
    __metaclass__ = ABCMeta

    def __init__(self, trading_mode):
        self.trading_mode = trading_mode
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
    def _check_factor(min_val, max_val, factor):
        if factor > max_val:
            return max_val
        elif factor < min_val:
            return min_val
        else:
            return factor

    @staticmethod
    def _trunc_with_n_decimal_digits(value, digits):
        # force exact representation
        return float("{0:.{1}f}".format(math.trunc(value*10**digits)/(10**digits), digits))

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
            valid_last_order_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, rest_order_quantity)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = (after_rest_quantity_to_adapt + max_value)/(nb_full_orders+1)
        valid_other_orders_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)]*int(nb_full_orders)
        return orders

    @staticmethod
    def _adapt_order_quantity_because_price(limiting_value, max_value, price, symbol_market):
        orders = []
        nb_full_orders = limiting_value // max_value
        rest_order_cost = limiting_value % max_value
        if rest_order_cost > 0:
            valid_last_order_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, rest_order_cost / price)
            orders.append((valid_last_order_quantity, price))

        other_orders_quantity = max_value / price
        valid_other_orders_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, other_orders_quantity)
        orders += [(valid_other_orders_quantity, price)] * int(nb_full_orders)
        return orders

    @staticmethod
    def _adapt_price(symbol_market, price):
        maximal_price_digits = AbstractTradingModeCreator._get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                                Ecmsc.PRECISION_PRICE.value,
                                                                                CURRENCY_DEFAULT_MAX_PRICE_DIGITS)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(price, maximal_price_digits)

    @staticmethod
    def _adapt_quantity(symbol_market, quantity):
        maximal_volume_digits = AbstractTradingModeCreator._get_value_or_default(symbol_market[Ecmsc.PRECISION.value],
                                                                                 Ecmsc.PRECISION_AMOUNT.value, 0)
        return AbstractTradingModeCreator._trunc_with_n_decimal_digits(quantity, maximal_volume_digits)

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

        min_quantity = AbstractTradingModeCreator._get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value)
        max_quantity = AbstractTradingModeCreator._get_value_or_default(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value)
        min_cost = AbstractTradingModeCreator._get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MIN.value)
        max_cost = AbstractTradingModeCreator._get_value_or_default(limit_cost, Ecmsc.LIMITS_COST_MAX.value)
        min_price = AbstractTradingModeCreator._get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MIN.value)
        max_price = AbstractTradingModeCreator._get_value_or_default(limit_price, Ecmsc.LIMITS_PRICE_MAX.value)

        # adapt digits if necessary
        valid_quantity = AbstractTradingModeCreator._adapt_quantity(symbol_market, quantity)
        valid_price = AbstractTradingModeCreator._adapt_price(symbol_market, price)

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
                return AbstractTradingModeCreator._adapt_order_quantity_because_price(total_order_price, max_cost, price,
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

    @abstractmethod
    def create_new_order(self, eval_note, symbol, exchange, trader, portfolio, state):
        raise NotImplementedError("Create_new_order not implemented")

    @abstractmethod
    def _get_limit_price_from_risk(self, eval_note, trader):
        raise NotImplementedError("Set_final_eval not implemented")

    @abstractmethod
    def _get_stop_price_from_risk(self, trader):
        raise NotImplementedError("Set_final_eval not implemented")

    @abstractmethod
    def _get_limit_quantity_from_risk(self, eval_note, trader, quantity):
        raise NotImplementedError("Set_final_eval not implemented")

    @abstractmethod
    def _get_market_quantity_from_risk(self, eval_note, trader, quantity, buy=False):
        raise NotImplementedError("Set_final_eval not implemented")
