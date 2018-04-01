from enum import Enum


class Trader:
    def __init__(self, exchange):
        self.exchange = exchange

    def create_order(self, type):
        pass


class TraderOrderType(Enum):
    BUY_MARKET = 1
    BUY_LIMIT = 2
    STOP_LOSS = 3
    SELL_MARKET = 4
    SELL_LIMIT = 5
