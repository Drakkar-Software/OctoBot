from binance.client import Client

from config.cst import *
import pandas
from aenum import MultiValueEnum
from exchanges.exchange import Exchange


class BinanceExchange(Exchange):
    def __init__(self, config):
        super().__init__(config)
        self.client = Client(self.config["exchanges"]["binance"]["api-key"],
                             self.config["exchanges"]["binance"]["api-secret"],
                             {"verify": True, "timeout": 20})

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

    def symbol_exists(self, symbol):
        if symbol in self.symbol_list:
            return True
        else:
            return False

    @staticmethod
    def get_time_frame_enum():
        return BinanceTimeFrames


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
