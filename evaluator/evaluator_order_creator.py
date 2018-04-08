from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self, config, evaluator):
        self.config = config
        self.evaluator = evaluator
        self.last_values_count = 10

    def create_order(self, trader):
        last_prices = self.evaluator.get_exchange().get_recent_trades(self.evaluator.get_symbol())
        reference_sum = 0

        for last_price in last_prices[-self.last_values_count:]:
            reference_sum += float(last_price["price"])

        reference = reference_sum / self.last_values_count

        currency, market = self.evaluator.exchange.split_symbol(self.evaluator.get_symbol())
        current_portfolio = trader.get_portfolio(currency)
        current_market_quantity = trader.get_portfolio(market)

        # TODO : temp
        if EvaluatorStates.VERY_SHORT:
            if current_portfolio > 0:
                trader.create_order(TraderOrderType.SELL_MARKET,
                                    self.evaluator.symbol,
                                    current_portfolio,
                                    reference)

        elif EvaluatorStates.SHORT:
            if current_portfolio > 0:
                trader.create_order(TraderOrderType.SELL_LIMIT,
                                    self.evaluator.symbol,
                                    current_portfolio / 2,
                                    reference * 0.9)

        elif EvaluatorStates.NEUTRAL:
            pass

        elif EvaluatorStates.LONG:
            if current_market_quantity > 0:
                trader.create_order(TraderOrderType.BUY_LIMIT,
                                    self.evaluator.symbol,
                                    current_market_quantity / (reference * 2),
                                    reference * 1.1)

        elif EvaluatorStates.VERY_LONG:
            if current_market_quantity > 0:
                trader.create_order(TraderOrderType.SELL_MARKET,
                                    self.evaluator.symbol,
                                    current_market_quantity / reference,
                                    reference)
