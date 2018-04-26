import json
import logging
import threading
import time
from logging.config import fileConfig

import ccxt

from config.config import load_config
from config.cst import CONFIG_ENABLED_OPTION, CONFIG_DATA_COLLECTOR, CONFIG_EXCHANGES, CONFIG_DATA_PATH, \
    DATA_COLLECTOR_REFRESHER_TIME, TimeFrames, TimeFramesMinutes, MINUTE_TO_SECONDS
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
        self.file = None
        self.file_content = None
        self.file_name = "{0}_{1}.data".format(self.exchange.get_name(), time.strftime("%Y%m%d_%H%M%S"))
        self.time_frame_update = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # TEMP
        self.symbol = "BTC/USDT"

    def stop(self):
        self.keep_running = False

    def update_file(self):
        file_content_json = {}
        for time_frame in self.file_content:
            file_content_json[time_frame] = self.file_content[time_frame].to_json()

        json.dump(file_content_json, self.file)

    def prepare_file(self):
        self.file = open(CONFIG_DATA_PATH + self.file_name, 'w')
        self.file_content = {}
        for time_frame in TimeFrames:
            self.file_content[time_frame.value] = None

    def prepare(self):
        self.logger.info("{0} prepare...".format(self.exchange.get_name()))
        self.prepare_file()
        for time_frame in TimeFrames:
            if self.exchange.time_frame_exists(time_frame.value):
                # write all available data for this time frame
                self.file_content[time_frame.value] = self.exchange.get_symbol_prices(self.symbol,
                                                                                      time_frame,
                                                                                      None)

                self.time_frame_update[time_frame] = time.time()
        self.update_file()

    def run(self):
        self.prepare()
        self.logger.info("{0} updating...".format(self.exchange.get_name()))
        while self.keep_running:
            now = time.time()

            for time_frame in TimeFrames:
                if self.exchange.time_frame_exists(time_frame.value):
                    if (time.time() - now) >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                        self.file_content[time_frame.value].concat(self.exchange.get_symbol_prices(self.symbol,
                                                                                                   time_frame,
                                                                                                   1))
                        self.time_frame_update[time_frame] = time.time()
                        self.logger.info("{0} : {1} updated".format(self.exchange.get_name(), time_frame))

            self.update_file()
            time.sleep(DATA_COLLECTOR_REFRESHER_TIME)


if __name__ == '__main__':
    fileConfig('config/logging_config.ini')
    global_config = load_config()

    if DataCollector.enabled(global_config):
        data_collector_inst = DataCollector(global_config)
        # data_collector_inst.stop()
        data_collector_inst.join()
