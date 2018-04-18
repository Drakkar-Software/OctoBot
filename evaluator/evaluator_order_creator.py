from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self):
        self.last_values_count = 10

    def create_order(self, symbol, exchange, trader, state):
        last_prices = exchange.get_recent_trades(symbol)
        reference_sum = 0

        for last_price in last_prices[-self.last_values_count:]:
            reference_sum += float(last_price["price"])

        reference = reference_sum / self.last_values_count

        currency, market = exchange.split_symbol(symbol)
        current_portfolio = trader.get_portfolio().get_currency_portfolio(currency)
        current_market_quantity = trader.get_portfolio().get_currency_portfolio(market)

        # TODO : temp
        if state == EvaluatorStates.VERY_SHORT:
            if current_portfolio > 0:
                trader.create_order(TraderOrderType.SELL_MARKET,
                                    symbol,
                                    current_portfolio,
                                    reference)

        elif state == EvaluatorStates.SHORT:
            if current_portfolio > 0:
                trader.create_order(TraderOrderType.SELL_LIMIT,
                                    symbol,
                                    current_portfolio / 2,
                                    reference * 1.005)

        elif state == EvaluatorStates.NEUTRAL:
            pass

        elif state == EvaluatorStates.LONG:
            if current_market_quantity > 0:
                trader.create_order(TraderOrderType.BUY_LIMIT,
                                    symbol,
                                    current_market_quantity / (reference * 2),
                                    reference * 0.999)

        elif state == EvaluatorStates.VERY_LONG:
            if current_market_quantity > 0:
                trader.create_order(TraderOrderType.BUY_MARKET,
                                    symbol,
                                    current_market_quantity / reference,
                                    reference)
