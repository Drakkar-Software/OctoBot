import logging
import threading
from logging.config import fileConfig

import ccxt

from config.config import load_config
from config.cst import CONFIG_ENABLED_OPTION, CONFIG_DATA_COLLECTOR, CONFIG_EXCHANGES
from trading import Exchange


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

                exchange_inst = Exchange(self.config, exchange_type)

                exchange_data_collector = ExchangeDataCollector(self.config, exchange_inst)
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

    @staticmethod
    def enabled(config):
        return CONFIG_DATA_COLLECTOR in config and config[CONFIG_DATA_COLLECTOR][CONFIG_ENABLED_OPTION]


class ExchangeDataCollector(threading.Thread):
    def __init__(self, config, exchange):
        super().__init__()
        self.config = config
        self.exchange = exchange
        self.keep_running = True

    def stop(self):
        self.keep_running = False

    def run(self):
        while self.keep_running:
            pass


if __name__ == '__main__':
    fileConfig('config/logging_config.ini')
    global_config = load_config()

    if DataCollector.enabled(global_config):
        data_collector_inst = DataCollector(global_config)
        # data_collector_inst.stop()
        data_collector_inst.join()
