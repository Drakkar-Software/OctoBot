from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self):
        self.last_values_count = 10

        self.STOP_LOSS_ORDER_MAX_PERCENT = 0.99
        self.STOP_LOSS_ORDER_MIN_PERCENT = 0.90
        self.STOP_LOSS_ORDER_ATTENUATION = 0.1

        self.QUANTITY_MIN_PERCENT = 0.1
        self.QUANTITY_MAX_PERCENT = 0.9
        self.QUANTITY_ATTENUATION = 0.3

        self.BUY_LIMIT_ORDER_MAX_PERCENT = 0.99
        self.BUY_LIMIT_ORDER_MIN_PERCENT = 0.80
        self.SELL_LIMIT_ORDER_MIN_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MAX_PERCENT)
        self.SELL_LIMIT_ORDER_MAX_PERCENT = 1 + (1 - self.BUY_LIMIT_ORDER_MIN_PERCENT)
        self.LIMIT_ORDER_ATTENUATION = 0.02

    @staticmethod
    def _check_factor(min_val, max_val, factor):
        if factor > max_val:
            return max_val
        elif factor < min_val:
            return min_val
        else:
            return factor

    def _get_limit_price_from_risk(self, eval_note, trader):
        if eval_note > 0:
            factor = self.SELL_LIMIT_ORDER_MIN_PERCENT + \
                     ((abs(eval_note) + trader.get_risk()) * self.LIMIT_ORDER_ATTENUATION)
            return EvaluatorOrderCreator._check_factor(self.SELL_LIMIT_ORDER_MIN_PERCENT,
                                                       self.SELL_LIMIT_ORDER_MAX_PERCENT,
                                                       factor)
        else:
            factor = self.BUY_LIMIT_ORDER_MAX_PERCENT - \
                     ((abs(eval_note) + trader.get_risk()) * self.LIMIT_ORDER_ATTENUATION)
            return EvaluatorOrderCreator._check_factor(self.BUY_LIMIT_ORDER_MIN_PERCENT,
                                                       self.BUY_LIMIT_ORDER_MAX_PERCENT,
                                                       factor)

    def _get_limit_quantity_from_risk(self, eval_note, trader, quantity):
        factor = self.QUANTITY_MIN_PERCENT + ((abs(eval_note) + trader.get_risk()) * self.QUANTITY_ATTENUATION)
        return EvaluatorOrderCreator._check_factor(self.QUANTITY_MIN_PERCENT,
                                                   self.QUANTITY_MAX_PERCENT,
                                                   factor) * quantity

    def _get_stop_price_from_risk(self, eval_note, trader):
        factor = self.STOP_LOSS_ORDER_MAX_PERCENT - \
                 ((abs(eval_note) + trader.get_risk()) * self.STOP_LOSS_ORDER_ATTENUATION)
        return EvaluatorOrderCreator._check_factor(self.STOP_LOSS_ORDER_MIN_PERCENT, self.STOP_LOSS_ORDER_MAX_PERCENT, factor)

    def create_order(self, eval_note, symbol, exchange, trader, state):
        last_prices = exchange.get_recent_trades(symbol)
        reference_sum = 0

        for last_price in last_prices[-self.last_values_count:]:
            reference_sum += float(last_price["price"])

        reference = reference_sum / self.last_values_count

        currency, market = exchange.split_symbol(symbol)
        current_portfolio = trader.get_portfolio().get_currency_portfolio(currency)
        current_market_quantity = trader.get_portfolio().get_currency_portfolio(market)
        market_quantity = current_market_quantity / reference

        # TODO : temp
        if state == EvaluatorStates.VERY_SHORT:
            if current_portfolio > 0:
                market = trader.create_order(TraderOrderType.SELL_MARKET,
                                             symbol,
                                             current_portfolio,
                                             reference)
                return market

        elif state == EvaluatorStates.SHORT:
            if current_portfolio > 0:
                limit = trader.create_order(TraderOrderType.SELL_LIMIT,
                                            symbol,
                                            self._get_limit_quantity_from_risk(eval_note,
                                                                               trader,
                                                                               current_portfolio),
                                            reference * self._get_limit_price_from_risk(eval_note,
                                                                                        trader))
                trader.create_order(TraderOrderType.STOP_LOSS,
                                    symbol,
                                    self._get_limit_quantity_from_risk(eval_note,
                                                                       trader,
                                                                       current_portfolio),
                                    reference * self._get_stop_price_from_risk(eval_note,
                                                                               trader),
                                    linked_to=limit)
                return limit

        elif state == EvaluatorStates.NEUTRAL:
            pass

        # TODO : stop loss
        elif state == EvaluatorStates.LONG:
            if current_market_quantity > 0:
                limit = trader.create_order(TraderOrderType.BUY_LIMIT,
                                            symbol,
                                            self._get_limit_quantity_from_risk(eval_note,
                                                                               trader,
                                                                               market_quantity),
                                            reference * self._get_limit_price_from_risk(eval_note,
                                                                                        trader))
                return limit

        elif state == EvaluatorStates.VERY_LONG:
            if current_market_quantity > 0:
                market = trader.create_order(TraderOrderType.BUY_MARKET,
                                             symbol,
                                             market_quantity,
                                             reference)
                return market
