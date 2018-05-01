import ccxt

from backtesting.collector.data_collector import DataCollectorParser
from backtesting.exchange_simulator import ExchangeSimulator
from config.cst import *

"""
Class containing data with known moves
Moves are in the middle of the return data_frame
"""


class DataBank:

    def __init__(self, config, data_file=None, symbols=None):
        self.config = config
        self.data_file = data_file if data_file else "tests/static/data_bank_reference.data"
        self.symbols = symbols if symbols else ["BTC"]
        self.exchange_inst = ExchangeSimulator(self.config, ccxt.binance)
        self.exchange_inst.data = self.get_data_from_file(self.data_file)
        self.data_by_symbol_by_data_frame = None
        self._init_data()

    def get_all_data_for_all_available_time_frames_for_symbol(self, symbol):
        return self.data_by_symbol_by_data_frame[symbol]

    # works only with default data file
    def get_sudden_pump(self):
        pass

    # -4: not started, -3: started, -2: heavy dump, -1: very light dump, max: stopped dump:
    def get_sudden_dump(self):
        return self._get_bank_time_frame_data(TimeFrames.ONE_HOUR)[0:46], -4, -3, -2, -1

    def _get_bank_time_frame_data(self, time_frame):
        return self.data_by_symbol_by_data_frame[self.symbols[0]][time_frame]

    @staticmethod
    def get_data_from_file(file_name):
        return DataCollectorParser.parse(file_name)

    def _init_data(self):
        self.data_by_symbol_by_data_frame = {symbol: self._get_symbol_data(symbol) for symbol in self.symbols}

    def _get_symbol_data(self, symbol):
        return {time_frame: self.exchange_inst.get_symbol_prices(
            symbol,
            time_frame,
            data_frame=True)
            for time_frame in TimeFrames
            if self.exchange_inst.has_data_for_time_frame(time_frame.value)}
