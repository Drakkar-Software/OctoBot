import logging

import ccxt

from backtesting.collector.exchange_collector import ExchangeDataCollector
from config.cst import CONFIG_TIME_FRAME, CONFIG_EXCHANGES
from trading.exchanges.exchange_manager import ExchangeManager


class DataCollector:
    def __init__(self, config, auto_start=True):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        self.exchange_data_collectors_threads = []

        self.config[CONFIG_TIME_FRAME] = []

        if auto_start:
            self.logger.info("Create data collectors...")
            self.create_exchange_data_collectors()

    def create_exchange_data_collectors(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False, rest_only=True)
                exchange_inst = exchange_manager.get_exchange()

                exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst)

                if not exchange_data_collector.get_symbols() or not exchange_data_collector.time_frames:
                    self.logger.warning("{0} exchange not started (not enough symbols or timeframes)"
                                        .format(exchange_class_string))
                else:
                    exchange_data_collector.start()
                    self.exchange_data_collectors_threads.append(exchange_data_collector)
            else:
                self.logger.error("{0} exchange not found".format(exchange_class_string))

    def execute_with_specific_target(self, exchange, symbol):
        exchange_type = getattr(ccxt, exchange)
        exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False, rest_only=True,
                                           ignore_config=True)
        exchange_inst = exchange_manager.get_exchange()
        exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst, symbol)
        files = exchange_data_collector.load_available_data()
        return files[0]

    def stop(self):
        for data_collector in self.exchange_data_collectors_threads:
            data_collector.stop()

    def join(self):
        for data_collector in self.exchange_data_collectors_threads:
            data_collector.join()
