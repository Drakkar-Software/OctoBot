import json
import logging
import os
import threading
import time
import gzip

from config.cst import *
from tools.symbol_util import merge_currencies


class ExchangeDataCollector(threading.Thread):
    Exchange_Data_Collector_File_Ext = ".data"

    def __init__(self, config, exchange):
        super().__init__()
        self.config = config
        self.exchange = exchange
        self.symbols = self.exchange.get_exchange_manager().get_traded_pairs()
        self.keep_running = True
        self.file = None
        self._data_updated = False

        self.file_names = {}
        self.file_contents = {}
        self.time_frame_update = {}

        self.time_frames = []
        for time_frame in TimeFrames:
            if self.exchange.get_exchange_manager().time_frame_exists(time_frame.value):
                self.time_frames.append(time_frame)

        self.logger = logging.getLogger(self.__class__.__name__)

    def get_symbols(self):
        return self.symbols

    def get_time_frames(self):
        return self.time_frames

    def stop(self):
        self.keep_running = False

    def _set_file_name(self, symbol):
        return "{0}_{1}_{2}{3}".format(self.exchange.get_name(),
                                       symbol.replace("/", "_"),
                                       time.strftime("%Y%m%d_%H%M%S"),
                                       self.Exchange_Data_Collector_File_Ext)

    @staticmethod
    def get_file_name(file_name):
        data = os.path.basename(file_name).split("_")
        try:
            exchange_name = data[0]
            symbol = merge_currencies(data[1], data[2])
            timestamp = data[3] + data[4].replace(ExchangeDataCollector.Exchange_Data_Collector_File_Ext, "")
        except KeyError:
            exchange_name = None
            symbol = None
            timestamp = None

        return exchange_name, symbol, timestamp

    def _prepare_files(self):
        for symbol in self.symbols:
            self.file_contents[symbol] = {}
            self.time_frame_update[symbol] = {}
            self.file_names[symbol] = self._set_file_name(symbol)
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
                                                                                               return_list=True)
                self.time_frame_update[symbol][time_frame] = time.time()
            self._update_file(symbol)

    def _update_file(self, symbol):
        file_name = CONFIG_DATA_COLLECTOR_PATH + self.file_names[symbol]
        with gzip.open(file_name, 'wt') as json_file:
            json.dump(self.file_contents[symbol], json_file)
            self.logger.info(f"{symbol} candles data saved in: {file_name}")

    def run(self):
        self._prepare()
        self.logger.info("{0} updating...".format(self.exchange.get_name()))
        while self.keep_running:
            now = time.time()

            for symbol in self.symbols:
                for time_frame in self.time_frames:
                    if now - self.time_frame_update[symbol][time_frame] \
                            >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                        result_df = self.exchange.get_symbol_prices(symbol,
                                                                    time_frame,
                                                                    limit=1,
                                                                    return_list=True)[0]

                        self.file_contents[symbol][time_frame.value].append(result_df)
                        self._data_updated = True
                        self.time_frame_update[symbol][time_frame] = now
                        self.logger.info(
                            "{0} ({2}) on {1} updated".format(symbol, self.exchange.get_name(), time_frame))

                if self._data_updated:
                    self._update_file(symbol)
                    self._data_updated = False

            final_sleep = DATA_COLLECTOR_REFRESHER_TIME - (time.time() - now)
            time.sleep(final_sleep if final_sleep >= 0 else 0)
