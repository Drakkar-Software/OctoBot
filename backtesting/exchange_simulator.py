from backtesting.collector.data_collector import DataCollectorParser
from config.cst import *
from trading import Exchange


class ExchangeSimulator(Exchange):
    def __init__(self, config, exchange_type):
        super().__init__(config, exchange_type)
        self.data = DataCollectorParser.parse(self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE])

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        test2 = self.data[time_frame.value]

        if data_frame:
            return self.candles_array_to_data_frame(test2)
        else:
            return test2
