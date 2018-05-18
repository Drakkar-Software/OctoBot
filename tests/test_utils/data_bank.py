import ccxt
import pandas

from config.cst import TimeFrames
from tools.data_visualiser import DataVisualiser
from trading.exchanges.exchange_manager import ExchangeManager

"""
Class containing data with known moves
Moves are in the middle of the return data_frame

TimeFrames.FIVE_MINUTES: 2018-04-26 17:00:00 -> 2018-04-27 02:00:00
TimeFrames.FIFTEEN_MINUTES: 2018-04-23 06:15:00 -> 2018-04-24 07:00:00
TimeFrames.ONE_HOUR: 2018-04-07 16:00:00 -> 2018-04-11 20:00:00
TimeFrames.FOUR_HOURS: 2018-02-03 00:00:00 -> 2018-02-20 16:00:00
TimeFrames.HEIGHT_HOURS: 2017-11-12 04:00:00 -> 2017-12-11 16:00:00
TimeFrames.ONE_DAY: 2017-08-17 00:00:00 -> 2017-11-12 00:00:00

"""


class DataBank:

    def __init__(self, config, data_file=None, symbols=None):
        self.config = config
        self.data_file = data_file if data_file else "tests/static/binance_BTC_USDT_20180428_121156.data"
        self.symbols = symbols if symbols else ["BTC"]

        exchange_manager = ExchangeManager(self.config, ccxt.binance, is_simulated=True)
        self.exchange_inst = exchange_manager.get_exchange()

        self.data_by_symbol_by_data_frame = None
        self._init_data()

    def get_all_data_for_all_available_time_frames_for_symbol(self, symbol):
        return self.data_by_symbol_by_data_frame[symbol]

    # works only with default data file
    # not started, selling started, selling maxed, buying starting, max: back normal:
    def get_rise_after_over_sold(self):
        return pandas.concat([self._get_bank_time_frame_data(TimeFrames.FOUR_HOURS)[35:61],
                              self._get_bank_time_frame_data(TimeFrames.FOUR_HOURS)])[0:49], \
            35, 43, 46, 47

    # works only with default data file
    # not started, buying started, buying maxed, start dipping, super dip, max: back normal:
    def get_dip_after_over_bought(self):
        return self._get_bank_time_frame_data(TimeFrames.ONE_DAY)[0:90], \
            -18, -14, -10, -9, -2

    # works only with default data file
    # not started, started, heavy dump, very light dump, max: stopped dump:
    def get_sudden_dump(self):
        return self._get_bank_time_frame_data(TimeFrames.ONE_HOUR)[0:46], \
            -4, -3, -2, -1

    # works only with default data file
    # not started, started, heavy pump, max pump, change trend, dipping, max: dipped:
    def get_sudden_pump(self):
        return self._get_bank_time_frame_data(TimeFrames.HEIGHT_HOURS)[:83], \
            71, 74, 76, 77, 78, 79

    # works only with default data file
    # long data_frame with flat then sudden big rise and then mostly flat for 120 values
    # start move ending up in a rise, reaches flat trend, first micro up p1, first mirco up p2, micro down, micro up,
    # micro down, micro up, micro down, back normal, micro down, back normal, micro down, back up, micro up, back down,
    # back normal, micro down, back up, micro down, back up, micro down, back up
    def get_overall_flat_trend(self):
        return pandas.concat([self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES)[6:72]*0.9,
                              self._get_bank_time_frame_data(TimeFrames.HEIGHT_HOURS)[25:43],
                              self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES)[6:72],
                              self._get_bank_time_frame_data(TimeFrames.FIFTEEN_MINUTES)[6:72]]), \
            67, 85, 87, 90, 95, 107, 116, 123, 138, 141, 151, 153, 161, 163, 173, 174, 175, 180, 183, 193, 198, 203, 207

    def _get_bank_time_frame_data(self, time_frame):
        return self.data_by_symbol_by_data_frame[self.symbols[0]][time_frame]

    def _init_data(self):
        self.data_by_symbol_by_data_frame = {symbol: self._get_symbol_data(symbol) for symbol in self.symbols}

    @staticmethod
    def show_data(data_frame):
        DataVisualiser.show_candlesticks_dataframe(data_frame)

    def _get_symbol_data(self, symbol):
        return {time_frame: self.exchange_inst.get_symbol_prices(
            symbol,
            time_frame,
            data_frame=True)
            for time_frame in TimeFrames
            if self.exchange_inst.get_exchange().has_data_for_time_frame(symbol, time_frame.value)}
