import time
from abc import *
from threading import Lock

from config.cst import TradeOrderSide, OrderStatus, TraderOrderType, SIMULATOR_LAST_PRICES_TO_CHECK

""" Order class will represent an open order in the specified exchange
In simulation it will also define rules to be filled / canceled
It is also use to store creation & fill values of the order """


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
        self.created_last_price = None

        self.order_notifier = None

        self.linked_orders = []
        self.lock = Lock()

    # Disposable design pattern
    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

    # create the order by setting all the required values
    def new(self, order_type, symbol, current_price, quantity, price=None, stop_price=None, order_notifier=None):
        self.origin_price = price
        self.last_prices = price
        self.created_last_price = current_price
        self.origin_quantity = quantity
        self.origin_stop_price = stop_price
        self.symbol = symbol
        self.order_type = order_type
        self.order_notifier = order_notifier
        self.currency, self.market = self.exchange.split_symbol(symbol)

        if not self.trader.simulate:
            # self.status, self.order_id, self.filled_price, self.filled_quantity, self.ex_time
            self.exchange.create_order(order_type, symbol, quantity, price, stop_price)
        else:
            self.status = OrderStatus.PENDING
            self.filled_quantity = quantity

    # update_order_status will define the rules for a simulated order to be filled / canceled
    @abstractmethod
    def update_order_status(self):
        raise NotImplementedError("Update_order_status not implemented")

    # check_last_prices is used to collect data to perform the order update_order_status process
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

    def cancel_order(self):
        self.status = OrderStatus.CANCELED
        # TODO exchange
        self.trader.notify_order_cancel(self)

    def close_order(self):
        self.trader.notify_order_close(self)

    def add_linked_order(self, order):
        self.linked_orders.append(order)

    def get_linked_orders(self):
        return self.linked_orders

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

    def get_origin_quantity(self):
        return self.origin_quantity

    def get_origin_price(self):
        return self.origin_price

    def get_order_notifier(self):
        return self.order_notifier

    def set_last_prices(self, last_prices):
        self.last_prices = last_prices

    def get_create_last_price(self):
        return self.created_last_price

    @classmethod
    def get_name(cls):
        return cls.__name__


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
        if not self.trader.simulate:
            # self.status, self.order_id, self.total_fees, self.filled_price, self.filled_quantity, self.executed_time =
            self.exchange.get_order(self.order_id)
        else:
            # ONLY FOR SIMULATION
            if self.check_last_prices(self.origin_price, True):
                self.status = OrderStatus.FILLED
                self.filled_price = self.origin_price
                self.executed_time = time.time()


# TODO
class StopLossLimitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


# TODO
class TakeProfitOrder(Order):
    def __init__(self, exchange):
        super().__init__(exchange)
        self.side = TradeOrderSide.SELL

    def update_order_status(self):
        pass


# TODO
class TakeProfitLimitOrder(Order):
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
