from binance.client import Client
from config.cst import *
import pandas

from exchanges.exchange import Exchange


class BinanceExchange(Exchange):
    def __init__(self, config):
        super().__init__(config)
        self.client = Client(self.config["exchanges"]["binance"]["api-key"],
                             self.config["exchanges"]["binance"]["api-secret"],
                             {"verify": True, "timeout": 20})

    # @return DataFrame of prices
    def get_symbol_prices(self, symbol, time_frame):
        candles = self.client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1DAY)
        prices = {PriceStrings.STR_PRICE_HIGH: [],
                  PriceStrings.STR_PRICE_LOW: [],
                  PriceStrings.STR_PRICE_OPEN: [],
                  PriceStrings.STR_PRICE_CLOSE: [],
                  PriceStrings.STR_PRICE_VOL: []}

        for c in candles:
            prices[PriceStrings.STR_PRICE_OPEN].append(float(c[1]))
            prices[PriceStrings.STR_PRICE_HIGH].append(float(c[2]))
            prices[PriceStrings.STR_PRICE_LOW].append(float(c[3]))
            prices[PriceStrings.STR_PRICE_CLOSE].append(float(c[4]))
            prices[PriceStrings.STR_PRICE_VOL].append(float(c[5]))

        return pandas.DataFrame(data=prices)

    @staticmethod
    def get_time_frame_enum():
        return BinanceTimeFrames


class BinanceTimeFrames(TimeFrames):
    ONE_HOUR = Client.KLINE_INTERVAL_1HOUR
    TWO_HOURS = Client.KLINE_INTERVAL_2HOUR
    FOUR_HOURS = Client.KLINE_INTERVAL_4HOUR
    ONE_DAY = Client.KLINE_INTERVAL_1DAY
    THREE_DAYS = Client.KLINE_INTERVAL_3DAY
    ONE_WEEK = Client.KLINE_INTERVAL_1WEEK
    ONE_MONTH = Client.KLINE_INTERVAL_1MONTH
