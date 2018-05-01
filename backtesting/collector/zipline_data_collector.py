import csv
import time

from backtesting.collector.data_collector import DataCollectorParser, ExchangeDataCollector
from config.cst import *

from zipline.data.bundles import register
from zipline.data.bundles.csvdir import csvdir_equities


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
