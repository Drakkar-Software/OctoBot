import logging

from config.cst import *
from exchanges.trader import Trader


class TraderSimulator(Trader):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
        self.portfolio = {"BTC": self.config["simulator"]["portfolio"]}
        self.risk = self.config["simulator"]["risk"]
        self.logger = logging.getLogger("TraderSimulator")

    def enabled(self):
        if self.config["simulator"]["enabled"]:
            return True
        else:
            return False

    def create_order(self, order_type, symbol, quantity, price=None, limit_price=None):
        self.logger.debug("Order creation : " + str(symbol) + " | " + str(order_type))

        if order_type == TraderOrderType.BUY_MARKET:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.BUY)

        elif order_type == TraderOrderType.BUY_LIMIT:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.BUY)

        elif order_type == TraderOrderType.TAKE_PROFIT:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)

        elif order_type == TraderOrderType.TAKE_PROFIT_LIMIT:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)

        elif order_type == TraderOrderType.SELL_MARKET:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)

        elif order_type == TraderOrderType.SELL_LIMIT:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)

        elif order_type == TraderOrderType.STOP_LOSS:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)

        elif order_type == TraderOrderType.STOP_LOSS_LIMIT:
            # status, _, total_fee, filled_price, filled_quantity, _ = self.exchange.create_test_order(order_type,
            #                                                                                          symbol,
            #                                                                                          quantity)
            total_fee = 0
            status = True
            filled_price = price
            filled_quantity = quantity

            self.update_portfolio(symbol, filled_quantity, filled_price, total_fee, status, TradeOrderSide.SELL)


