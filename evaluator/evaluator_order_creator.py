from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self):
        self.last_values_count = 10

    @staticmethod
    def check_factor(min, max, factor):
        if factor > max:
            return max
        elif factor < min:
            return min
        else:
            return factor

    @staticmethod
    def get_limit_price_from_risk(eval_note, trader):
        if eval_note > 0:
            attenuate = 0.2
            factor = 1 + (1 - eval_note) * trader.get_risk() * attenuate
            return EvaluatorOrderCreator.check_factor(1.01, 1.25, factor)
        else:
            attenuate = 0.2
            factor = (1 + eval_note) * trader.get_risk() * attenuate
            return EvaluatorOrderCreator.check_factor(0.75, 0.99, factor)

    @staticmethod
    def get_limit_quantity_from_risk(eval_note, trader, quantity):
        multi = 1.5
        factor = abs(eval_note) * trader.get_risk() * multi
        return EvaluatorOrderCreator.check_factor(0.1, 0.9, factor) * quantity

    @staticmethod
    def get_stop_price_from_risk(eval_note, trader):
        attenuate = 0.5
        factor = 0.99 - (abs(eval_note) * trader.get_risk() * attenuate)
        return EvaluatorOrderCreator.check_factor(0.75, 0.99, factor)

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
                                            self.get_limit_quantity_from_risk(eval_note,
                                                                              trader,
                                                                              current_portfolio),
                                            reference * self.get_limit_price_from_risk(eval_note,
                                                                                       trader))
                trader.create_order(TraderOrderType.STOP_LOSS,
                                    symbol,
                                    self.get_limit_quantity_from_risk(eval_note,
                                                                      trader,
                                                                      current_portfolio),
                                    reference * self.get_stop_price_from_risk(eval_note,
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
                                            self.get_limit_quantity_from_risk(eval_note,
                                                                              trader,
                                                                              market_quantity),
                                            reference * self.get_limit_price_from_risk(eval_note,
                                                                                       trader))
                return limit

        elif state == EvaluatorStates.VERY_LONG:
            if current_market_quantity > 0:
                market = trader.create_order(TraderOrderType.BUY_MARKET,
                                             symbol,
                                             market_quantity,
                                             reference)
                return market
