from backtesting.collector.data_collector import DataCollectorParser
from config.cst import *
from trading import Exchange


class ExchangeSimulator(Exchange):
    def __init__(self, config, exchange_type):
        super().__init__(config, exchange_type)
        self.data = DataCollectorParser.parse(self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE])
