import logging

from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self):
        self.last_values_count = 10

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
        self.QUANTITY_MARKET_ATTENUATION = (self.QUANTITY_MARKET_MAX_PERCENT - self.QUANTITY_MARKET_MIN_PERCENT) / self.MAX_SUM_RESULT

        self.BUY_LIMIT_ORDER_MAX_PERCENT = 0.995
        self.BUY_LIMIT_ORDER_MIN_PERCENT = 0.98
        self.SELL_LIMIT_ORDER_MIN_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MAX_PERCENT)
        self.SELL_LIMIT_ORDER_MAX_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MIN_PERCENT)
        self.LIMIT_ORDER_ATTENUATION = (
                                                   self.BUY_LIMIT_ORDER_MAX_PERCENT - self.BUY_LIMIT_ORDER_MIN_PERCENT) / self.MAX_SUM_RESULT

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

    @staticmethod
    def can_create_order(symbol, exchange, trader, state):
        currency, market = exchange.split_symbol(symbol)
        portfolio = trader.get_portfolio()

        # todo : > min exchange
        # short cases => sell => need this currency
        if state == EvaluatorStates.VERY_SHORT or state == EvaluatorStates.SHORT:
            with portfolio as pf:
                return pf.get_currency_portfolio(currency) > MARKET_MIN_PORTFOLIO_CREATE_ORDER

        # long cases => buy => need money(aka other currency in the pair) to buy this currency
        elif state == EvaluatorStates.LONG or state == EvaluatorStates.VERY_LONG:
            with portfolio as pf:
                return pf.get_currency_portfolio(market) > CURRENCY_MIN_PORTFOLIO_CREATE_ORDER

        # other cases like neutral state or unfulfilled previous conditions
        return False

    # creates a new order, always check EvaluatorOrderCreator.can_create_order() first.
    def create_new_order(self, eval_note, symbol, exchange, trader, state):
        try:
            last_prices = exchange.get_recent_trades(symbol)
            portfolio = trader.get_portfolio()
            reference_sum = 0

            for last_price in last_prices[-self.last_values_count:]:
                reference_sum += float(last_price["price"])

            reference = reference_sum / self.last_values_count

            currency, market = exchange.split_symbol(symbol)

            with portfolio as pf:
                current_portfolio = pf.get_currency_portfolio(currency)
                current_market_quantity = pf.get_currency_portfolio(market)

            market_quantity = current_market_quantity / reference

            # TODO : temp
            if state == EvaluatorStates.VERY_SHORT:
                market = trader.create_order(TraderOrderType.SELL_MARKET,
                                             symbol,
                                             reference,
                                             self._get_market_quantity_from_risk(eval_note,
                                                                                 trader,
                                                                                 current_portfolio),
                                             reference)
                return market

            elif state == EvaluatorStates.SHORT:
                limit = trader.create_order(TraderOrderType.SELL_LIMIT,
                                            symbol,
                                            reference,
                                            self._get_limit_quantity_from_risk(eval_note,
                                                                               trader,
                                                                               current_portfolio),
                                            reference * self._get_limit_price_from_risk(eval_note,
                                                                                        trader))
                trader.create_order(TraderOrderType.STOP_LOSS,
                                    symbol,
                                    reference,
                                    self._get_limit_quantity_from_risk(eval_note,
                                                                       trader,
                                                                       current_portfolio),
                                    reference * self._get_stop_price_from_risk(trader),
                                    linked_to=limit)
                return limit

            elif state == EvaluatorStates.NEUTRAL:
                pass

            # TODO : stop loss
            elif state == EvaluatorStates.LONG:
                limit = trader.create_order(TraderOrderType.BUY_LIMIT,
                                            symbol,
                                            reference,
                                            self._get_limit_quantity_from_risk(eval_note,
                                                                               trader,
                                                                               market_quantity),
                                            reference * self._get_limit_price_from_risk(eval_note,
                                                                                        trader))
                return limit

            elif state == EvaluatorStates.VERY_LONG:
                market = trader.create_order(TraderOrderType.BUY_MARKET,
                                             symbol,
                                             reference,
                                             self._get_market_quantity_from_risk(eval_note,
                                                                                 trader,
                                                                                 market_quantity,
                                                                                 True),
                                             reference)
                return market

        except Exception as e:
            logging.getLogger(self.__class__.__name__).error("Failed to create order : {0}".format(e))
            return None
