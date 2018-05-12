import json
import logging
import threading
import time
import os.path

import ccxt

from config.cst import *
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


class DataCollectorParser:
    @staticmethod
    def parse(file):
        if os.path.isfile(CONFIG_DATA_COLLECTOR_PATH + file):
            with open(CONFIG_DATA_COLLECTOR_PATH + file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
        else:
            with open(file) as file_to_parse:
                file_content = json.loads(file_to_parse.read())
        return file_content


class ExchangeDataCollector(threading.Thread):
    def __init__(self, config, exchange):
        super().__init__()
        self.config = config
        self.exchange = exchange
        self.symbols = self.exchange.get_traded_pairs()
        self.keep_running = True
        self.file = None
        self._data_updated = False

        self.file_names = {}
        self.file_contents = {}
        self.time_frame_update = {}

        self.time_frames = []
        for time_frame in TimeFrames:
            if self.exchange.time_frame_exists(time_frame.value):
                self.time_frames.append(time_frame)

        self.logger = logging.getLogger(self.__class__.__name__)

    def stop(self):
        self.keep_running = False

    def _prepare_files(self):
        for symbol in self.symbols:
            self.file_contents[symbol] = {}
            self.time_frame_update[symbol] = {}
            self.file_names[symbol] = "{0}_{1}_{2}.data".format(self.exchange.get_name(),
                                                                symbol.replace("/", "_"),
                                                                time.strftime("%Y%m%d_%H%M%S"))
            for time_frame in self.time_frames:
                self.file_contents[symbol][time_frame.value] = None

    def _prepare(self):
        self.logger.info("{0} prepare...".format(self.exchange.get_name()))
        self._prepare_files()
        for symbol in self.symbols:
            for time_frame in self.time_frames:
                # write all available data for this time frame
                self.file_contents[symbol][time_frame.value] = self.exchange.get_symbol_prices(symbol,
                                                                                               time_frame,
                                                                                               limit=None,
                                                                                               data_frame=False)
                self.time_frame_update[symbol][time_frame] = time.time()
            self._update_file(symbol)

    def _update_file(self, symbol):
        with open(CONFIG_DATA_COLLECTOR_PATH + self.file_names[symbol], 'w') as json_file:
            json.dump(self.file_contents[symbol], json_file)

    def run(self):
        self._prepare()
        self.logger.info("{0} updating...".format(self.exchange.get_name()))
        while self.keep_running:
            now = time.time()

            for symbol in self.symbols:
                for time_frame in self.time_frames:
                    if now - self.time_frame_update[symbol][time_frame] >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                        result_df = self.exchange.get_symbol_prices(symbol,
                                                                    time_frame,
                                                                    limit=1,
                                                                    data_frame=False)[0]

                        self.file_contents[symbol][time_frame.value].append(result_df)
                        self._data_updated = True
                        self.time_frame_update[symbol][time_frame] = now
                        self.logger.info("{0} ({2}) on {1} updated".format(symbol, self.exchange.get_name(), time_frame))

                if self._data_updated:
                    self._update_file(symbol)
                    self._data_updated = False

            final_sleep = DATA_COLLECTOR_REFRESHER_TIME - (time.time() - now)
            time.sleep(final_sleep if final_sleep >= 0 else 0)
