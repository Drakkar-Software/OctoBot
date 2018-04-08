import logging

from binance.client import Client

from config.cst import *
import pandas
from aenum import MultiValueEnum
from exchanges.exchange import Exchange


class BinanceExchange(Exchange):
    def __init__(self, config):
        super().__init__(config)
        self.name = "Binance"
        self.logger = logging.getLogger(self.name + "Exchange")
        self.create_client()

    @staticmethod
    def get_time_frame_enum():
        return BinanceTimeFrames

    @staticmethod
    def get_order_type_enum():
        return BinanceOrderType

    def create_client(self):
        if self.enabled():
            if self.check_config():
                self.client = Client(self.config["exchanges"][self.name]["api-key"],
                                     self.config["exchanges"][self.name]["api-secret"],
                                     {"verify": True, "timeout": 20})
                self.connected = True
            else:
                self.client = Client(None, None, {"timeout": 20})
        else:
            self.logger.debug("Disabled")

    def check_config(self):
        if not self.config["exchanges"][self.name]["api-key"] \
                and not self.config["exchanges"][self.name]["api-secret"]:
            return False
        else:
            return True

    # @return DataFrame of prices
    def get_symbol_prices(self, symbol, time_frame):
        candles = self.client.get_klines(symbol=symbol, interval=time_frame.value)
        prices = {PriceStrings.STR_PRICE_HIGH.value: [],
                  PriceStrings.STR_PRICE_LOW.value: [],
                  PriceStrings.STR_PRICE_OPEN.value: [],
                  PriceStrings.STR_PRICE_CLOSE.value: [],
                  PriceStrings.STR_PRICE_VOL.value: []}

        for c in candles:
            prices[PriceStrings.STR_PRICE_OPEN.value].append(float(c[1]))
            prices[PriceStrings.STR_PRICE_HIGH.value].append(float(c[2]))
            prices[PriceStrings.STR_PRICE_LOW.value].append(float(c[3]))
            prices[PriceStrings.STR_PRICE_CLOSE.value].append(float(c[4]))
            prices[PriceStrings.STR_PRICE_VOL.value].append(float(c[5]))

        return pandas.DataFrame(data=prices)

    def get_symbol_list(self):
        for symbol_data in self.client.get_exchange_info()["symbols"]:
            self.symbol_list.append(symbol_data["symbol"])

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        if self.connected:
            side, *_ = order_type
            _, order, *_ = order_type

            order_result = self.client.create_order(
                symbol=symbol,
                side=side,
                type=order,
                quantity=quantity,
                price=price,
                stopPrice=stop_price,
                timeInForce=Client.TIME_IN_FORCE_GTC,
            )

            status, order_id, total_fee, filled_price, filled_quantity, transaction_time = self.parse_order_result(
                order_result)

            if symbol in self.balance:
                old = self.balance[symbol]
            else:
                old = 0

            if side == Client.SIDE_BUY:
                new_quantity = old + filled_quantity
            else:
                new_quantity = old - filled_quantity

            self.set_balance(symbol, new_quantity)

    def create_test_order(self, order_type, symbol, quantity, price=None, stop_price=None):
            if self.connected:
            side, *_ = order_type
            _, order, *_ = order_type

            order_result = self.client.create_test_order(
                symbol=symbol,
                side=side,
                type=order,
                quantity=quantity,
                price=price,
                stopPrice=stop_price,
                timeInForce=Client.TIME_IN_FORCE_GTC,
            )

            status, order_id, total_fee, filled_price, filled_quantity, transaction_time = self.parse_order_result(
                order_result)

            if symbol in self.balance:
                old = self.balance[symbol]
            else:
                old = 0

            if side == Client.SIDE_BUY:
                new_quantity = old + filled_quantity
            else:
                new_quantity = old - filled_quantity

            self.set_balance(symbol, new_quantity)

    @staticmethod
    def parse_order_result(result):
        order_id = result["orderId"]
        transaction_time = result["transactTime"]
        filled_price = result["price"]
        filled_quantity = result["executedQty"]
        status = result["status"]

        total_fee = 0
        for filled in result["fills"]:
            total_fee += filled["commission"]

        return status, order_id, total_fee, filled_price, filled_quantity, transaction_time

    def update_balance(self, symbol):
        if self.connected:
            self.set_balance(symbol, self.client.get_asset_balance(asset=symbol))

    def get_order(self, order_id):
        self.client.get_order(orderId=order_id)

    def get_open_orders(self):
        self.client.get_open_orders()

    def cancel_order(self, order_id):
        self.client.cancel_order(orderId=order_id)

    def get_trade_history(self):
        pass

    def get_all_orders(self):
        self.client.get_all_orders()


class BinanceTimeFrames(MultiValueEnum):
    ONE_MINUTE = Client.KLINE_INTERVAL_1MINUTE, TimeFrames.ONE_MINUTE
    FIVE_MINUTES = Client.KLINE_INTERVAL_5MINUTE, TimeFrames.FIVE_MINUTES
    THIRTY_MINUTES = Client.KLINE_INTERVAL_30MINUTE, TimeFrames.THIRTY_MINUTES
    ONE_HOUR = Client.KLINE_INTERVAL_1HOUR, TimeFrames.ONE_HOUR
    TWO_HOURS = Client.KLINE_INTERVAL_2HOUR, TimeFrames.TWO_HOURS
    FOUR_HOURS = Client.KLINE_INTERVAL_4HOUR, TimeFrames.FOUR_HOURS
    ONE_DAY = Client.KLINE_INTERVAL_1DAY, TimeFrames.ONE_DAY
    THREE_DAYS = Client.KLINE_INTERVAL_3DAY, TimeFrames.THREE_DAYS
    ONE_WEEK = Client.KLINE_INTERVAL_1WEEK, TimeFrames.ONE_WEEK
    ONE_MONTH = Client.KLINE_INTERVAL_1MONTH, TimeFrames.ONE_MONTH


class BinanceOrderType(MultiValueEnum):
    BUY_MARKET = frozenset([Client.SIDE_BUY, Client.ORDER_TYPE_MARKET]), TraderOrderType.BUY_MARKET
    BUY_LIMIT = frozenset([Client.SIDE_BUY, Client.ORDER_TYPE_LIMIT]), TraderOrderType.BUY_LIMIT
    TAKE_PROFIT = frozenset([Client.SIDE_SELL, Client.ORDER_TYPE_TAKE_PROFIT]), TraderOrderType.TAKE_PROFIT
    TAKE_PROFIT_LIMIT = frozenset(
        [Client.SIDE_SELL, Client.ORDER_TYPE_TAKE_PROFIT_LIMIT]), TraderOrderType.TAKE_PROFIT_LIMIT
    STOP_LOSS = frozenset([Client.SIDE_SELL, Client.ORDER_TYPE_STOP_LOSS]), TraderOrderType.STOP_LOSS
    STOP_LOSS_LIMIT = frozenset([Client.SIDE_SELL, Client.ORDER_TYPE_STOP_LOSS_LIMIT]), TraderOrderType.STOP_LOSS_LIMIT
    SELL_MARKET = frozenset([Client.SIDE_SELL, Client.ORDER_TYPE_MARKET]), TraderOrderType.SELL_MARKET
    SELL_LIMIT = frozenset([Client.SIDE_SELL, Client.ORDER_TYPE_LIMIT]), TraderOrderType.SELL_LIMIT
