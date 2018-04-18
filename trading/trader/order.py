import time
from abc import *

from config.cst import TradeOrderSide, OrderStatus, TraderOrderType, SIMULATOR_LAST_PRICES_TO_CHECK


class Order:
    __metaclass__ = ABCMeta

    def __init__(self, trader):
        super().__init__()
        self.trader = trader
        self.exchange = self.trader.get_exchange()
        self.side = None
        self.symbol = None
        self.origin_price = 0
        self.origin_stop_price = 0
        self.origin_quantity = 0
        self.market_total_fees = 0
        self.currency_total_fees = 0
        self.filled_quantity = 0
        self.filled_price = 0
        self.currency, self.market = None, None
        self.order_id = None
        self.status = None
        self.order_type = None
        self.executed_time = 0
        self.last_prices = None

    def new(self, order_type, symbol, quantity, price=None, stop_price=None):
        self.origin_price = price
        self.last_prices = price
        self.origin_quantity = quantity
        self.origin_stop_price = stop_price
        self.symbol = symbol
        self.order_type = order_type
        self.currency, self.market = self.exchange.split_symbol(symbol)
        if not self.trader.simulate:
            # self.status, self.order_id, self.filled_price, self.filled_quantity, self.ex_time
            self.exchange.create_order(order_type, symbol, quantity, price, stop_price)
        else:
            self.status = OrderStatus.PENDING
            self.filled_quantity = quantity

    @abstractmethod
    def update_order_status(self):
        raise NotImplementedError("Update_order_status not implemented")

    def check_last_prices(self, price, inferior):
        # TODO : use timestamp
        prices = [p["price"] for p in self.last_prices[-SIMULATOR_LAST_PRICES_TO_CHECK:]]

        if inferior:
            if float(min(prices)) < price:
                return True
            else:
                return False
        else:
            if float(max(prices)) > price:
                return True
            else:
                return False

    def close_order(self):
        self.trader.notify_order_close(self)

    def get_currency_and_market(self):
        return self.currency, self.market

    def get_side(self):
        return self.side

    def get_id(self):
        return self.order_id

    def get_market_total_fees(self):
        return self.market_total_fees

    def get_currency_total_fees(self):
        return self.currency_total_fees

    def get_filled_quantity(self):
        return self.filled_quantity

    def get_filled_price(self):
        return self.filled_price

    def get_status(self):
        return self.status

    def get_order_type(self):
        return self.order_type

    def get_order_symbol(self):
        return self.symbol

    def set_last_prices(self, last_prices):
        self.last_prices = last_prices


class BuyMarketOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.BUY

    def update_order_status(self):
        if not self.trader.simulate:
            # self.status, self.order_id, self.total_fees, self.filled_price, self.filled_quantity, self.executed_time =
            self.exchange.get_order(self.order_id)
        else:
            # ONLY FOR SIMULATION
            self.status = OrderStatus.FILLED
            self.filled_price = float(self.last_prices[-1]["price"])
            self.executed_time = time.time()


class BuyLimitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.BUY

    def update_order_status(self):
        if not self.trader.simulate:
            # self.status, self.order_id, self.total_fees, self.filled_price, self.filled_quantity, self.executed_time =
            self.exchange.get_order(self.order_id)
        else:
            # ONLY FOR SIMULATION
            if self.check_last_prices(self.origin_price, True):
                self.status = OrderStatus.FILLED
                self.filled_price = self.origin_price
                self.executed_time = time.time()


class TakeProfitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


class TakeProfitLimitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


class SellMarketOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        if not self.trader.simulate:
            # self.status, self.order_id, self.total_fees, self.filled_price, self.filled_quantity, self.executed_time =
            self.exchange.get_order(self.order_id)
        else:
            # ONLY FOR SIMULATION
            self.status = OrderStatus.FILLED
            self.filled_price = float(self.last_prices[-1]["price"])
            self.executed_time = time.time()


class SellLimitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        if not self.trader.simulate:
            # self.status, self.order_id, self.total_fees, self.filled_price, self.filled_quantity, self.executed_time =
            self.exchange.get_order(self.order_id)
        else:
            # ONLY FOR SIMULATION
            if self.check_last_prices(self.origin_price, False):
                self.status = OrderStatus.FILLED
                self.filled_price = self.origin_price
                self.executed_time = time.time()


class StopLossOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


class StopLossLimitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


class OrderConstants:
    TraderOrderTypeClasses = {
        TraderOrderType.BUY_MARKET: BuyMarketOrder,
        TraderOrderType.BUY_LIMIT: BuyLimitOrder,
        TraderOrderType.TAKE_PROFIT: TakeProfitOrder,
        TraderOrderType.TAKE_PROFIT_LIMIT: TakeProfitLimitOrder,
        TraderOrderType.STOP_LOSS: StopLossOrder,
        TraderOrderType.STOP_LOSS_LIMIT: StopLossLimitOrder,
        TraderOrderType.SELL_MARKET: SellMarketOrder,
        TraderOrderType.SELL_LIMIT: SellLimitOrder,
    }
