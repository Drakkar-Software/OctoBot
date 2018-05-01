import csv
import time

import ccxt

from backtesting.collector.data_collector import DataCollectorParser, ExchangeDataCollector, DataCollector
from config.cst import *


# from zipline.data.bundles import register
# from zipline.data.bundles.csvdir import csvdir_equities
from trading import Exchange


class ZiplineDataCollector(DataCollector):
    def __init__(self, config):
        super().__init__(config)

    def create_exchange_data_collectors(self):
        available_exchanges = ccxt.exchanges
        for exchange_class_string in self.config[CONFIG_EXCHANGES]:
            if exchange_class_string in available_exchanges:
                exchange_type = getattr(ccxt, exchange_class_string)

                exchange_inst = Exchange(self.config, exchange_type)

                exchange_data_collector = ZiplineExchangeDataCollector(self.config, exchange_inst)
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


class ZiplineDataCollectorParser(DataCollectorParser):
    @staticmethod
    def parse(file):
        with open(CONFIG_DATA_COLLECTOR_PATH + file) as file_to_parse:
            file_content = json.loads(file_to_parse.read())

        return file_content


class ZiplineExchangeDataCollector(ExchangeDataCollector):
    def __init__(self, config, exchange):
        super().__init__(config, exchange)
        self.file_name = "{0}_{1}_{2}.csv".format(self.exchange.get_name(),
                                                  self.symbol.replace("/", "_"),
                                                  time.strftime("%Y%m%d_%H%M%S"))

    def _update_file(self):
        with open(CONFIG_DATA_COLLECTOR_PATH + self.file_name, "wb") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter='', quotechar='"', quoting=csv.QUOTE_ALL)
            # self.file_content
