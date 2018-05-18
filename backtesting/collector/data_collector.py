import logging

import ccxt

from backtesting.collector.exchange_collector import ExchangeDataCollector
from config.cst import *
from trading.exchanges.exchange_manager import ExchangeManager


class DataCollector:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        self.exchange_data_collectors_threads = []
        self.logger.info("Create data collectors...")

        self.create_exchange_data_collectors()

    def create_exchange_data_collectors(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                exchange_manager = ExchangeManager(self.config, exchange_type, is_simulated=False)
                exchange_inst = exchange_manager.get_exchange()

                exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst)

                if len(exchange_data_collector.get_symbols()) == 0 or len(exchange_data_collector.time_frames) == 0:
                    self.logger.warning("{0} exchange not started (not enough symbols or timeframes)"
                                        .format(exchange_class_string))
                else:
                    exchange_data_collector.start()
                    self.exchange_data_collectors_threads.append(exchange_data_collector)
            else:
                self.logger.error("{0} exchange not found".format(exchange_class_string))

    def stop(self):
        for data_collector in self.exchange_data_collectors_threads:
            data_collector.stop()

    def join(self):
        for data_collector in self.exchange_data_collectors_threads:
            data_collector.join()
