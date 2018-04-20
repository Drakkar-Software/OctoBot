from config.cst import *


class EvaluatorOrderCreator:
    def __init__(self):
        self.last_values_count = 10

    def create_order(self, eval_note, symbol, exchange, trader, state):
        created_orders = []
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
                market = trader.create_order(TraderOrderType.SELL_MARKET,
                                             symbol,
                                             current_portfolio,
                                             reference)
                # notify creation
                market.get_order_notifier().notify()
                created_orders = [market]

        elif state == EvaluatorStates.SHORT:
            if current_portfolio > 0:
                quantity = current_portfolio / 2
                limit = trader.create_order(TraderOrderType.SELL_LIMIT,
                                            symbol,
                                            quantity,
                                            reference * (1 + eval_note * 0.1))
                stop = trader.create_order(TraderOrderType.STOP_LOSS,
                                           symbol,
                                           quantity,
                                           reference * STOP_LOSS_ORDER_PERCENT,
                                           linked_to=limit)
                # notify creation
                stop.get_order_notifier().notify()
                created_orders = [limit, stop]

        elif state == EvaluatorStates.NEUTRAL:
            pass

        # TODO : stop loss
        elif state == EvaluatorStates.LONG:
            if current_market_quantity > 0:
                limit = trader.create_order(TraderOrderType.BUY_LIMIT,
                                            symbol,
                                            current_market_quantity / (reference * 2),
                                            reference * (1 + eval_note * 0.1))
                # notify creation
                limit.get_order_notifier().notify()
                created_orders = [limit]

        elif state == EvaluatorStates.VERY_LONG:
            if current_market_quantity > 0:
                market = trader.create_order(TraderOrderType.BUY_MARKET,
                                             symbol,
                                             current_market_quantity / reference,
                                             reference)
                # notify creation
                market.get_order_notifier().notify()
                created_orders = [market]

        return created_orders
