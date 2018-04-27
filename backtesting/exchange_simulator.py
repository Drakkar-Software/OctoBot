from ccxt import BaseError

from backtesting.collector.data_collector import DataCollectorParser
from config.cst import *
from trading import Exchange


class ExchangeSimulator(Exchange):
    def __init__(self, config, exchange_type):
        super().__init__(config, exchange_type)
        self.data = DataCollectorParser.parse(self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE])
        self.time_frame_get_times = {}
        self.all_currencies_price_ticker = None
        self.fetched_trades = {}

        self.DEFAULT_LIMIT = 100

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        self.increase_time_frame_get_times(time_frame)
        result = self.extract_data_with_limit(time_frame)

        if data_frame:
            return self.candles_array_to_data_frame(result)
        else:
            return result

    def increase_time_frame_get_times(self, time_frame):
        if time_frame.value not in self.time_frame_get_times:
            self.time_frame_get_times[time_frame.value] = 0
        else:
            self.time_frame_get_times[time_frame.value] += 1

    def extract_data_with_limit(self, time_frame):
        full = self.data[time_frame.value]
        index = self.time_frame_get_times[time_frame.value]
        max_limit = len(full)

        if max_limit - index < self.DEFAULT_LIMIT:
            return full[index::]
        else:
            return full[index:self.DEFAULT_LIMIT]

    # TODO TEMP
    def get_all_currencies_price_ticker(self):
        if self.all_currencies_price_ticker is None:
            self.all_currencies_price_ticker = self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        else:
            return self.all_currencies_price_ticker

    # TODO TEMP
    def get_recent_trades(self, symbol):
        try:
            if symbol not in self.fetched_trades:
                self.fetched_trades[symbol] = self.client.fetch_trades(symbol)
        except BaseError as e:
            self.logger.error("Failed to get recent trade {0}".format(e))
            return None
        return self.fetched_trades[symbol]
