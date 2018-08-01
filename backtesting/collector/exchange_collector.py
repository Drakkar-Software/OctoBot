import logging
import threading
import time

from config.cst import *
from backtesting.collector.data_file_manager import build_file_name, write_data_file


class ExchangeDataCollector(threading.Thread):

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

    def _prepare_files_content(self):
        for symbol in self.symbols:
            self.file_contents[symbol] = {}
            self.time_frame_update[symbol] = {}
            self.file_names[symbol] = build_file_name(self.exchange, symbol)
            for time_frame in self.time_frames:
                self.file_contents[symbol][time_frame.value] = None

    def _prepare(self):
        self.logger.info("{0} prepare...".format(self.exchange.get_name()))
        self._prepare_files_content()
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
        write_data_file(file_name, self.file_contents[symbol])
        self.logger.info(f"{symbol} candles data saved in: {file_name}")

    def run(self):
        self._prepare()
        self.logger.info(f"Data Collector will now update this file from {self.exchange.get_name()} "
                         f"for each new time frame update...")
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
                        self.logger.info(f"{symbol} ({self.exchange.get_name()}) on {time_frame} updated")

                if self._data_updated:
                    self._update_file(symbol)
                    self._data_updated = False

            final_sleep = DATA_COLLECTOR_REFRESHER_TIME - (time.time() - now)
            time.sleep(final_sleep if final_sleep >= 0 else 0)
