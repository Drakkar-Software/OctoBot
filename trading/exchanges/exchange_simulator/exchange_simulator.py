import time
import datetime
import copy

from backtesting import get_bot
from backtesting.backtesting import Backtesting
from backtesting.collector.data_parser import DataCollectorParser
from backtesting.collector.exchange_collector import ExchangeDataCollector
from config.cst import TimeFrames, ExchangeConstantsMarketStatusColumns, CONFIG_BACKTESTING, \
    SIMULATOR_LAST_PRICES_TO_CHECK, ORDER_CREATION_LAST_TRADES_TO_USE,CONFIG_BACKTESTING_DATA_FILES, PriceIndexes, \
    TimeFramesMinutes, ExchangeConstantsTickersColumns
from tools.time_frame_manager import TimeFrameManager
from trading import AbstractExchange


class ExchangeSimulator(AbstractExchange):
    def __init__(self, config, exchange_type, exchange_manager):
        super().__init__(config, exchange_type)
        self.exchange_manager = exchange_manager

        if CONFIG_BACKTESTING not in self.config:
            raise Exception("Backtesting config not found")

        self.symbols = None
        self.data = None
        self._get_symbol_list()

        self.config_time_frames = TimeFrameManager.get_config_time_frame(self.config)

        # set exchange manager attributes
        self.exchange_manager.client_symbols = self.symbols
        self.exchange_manager.traded_pairs = self.symbols
        self.exchange_manager.client_time_frames = [tf.value for tf in self.config_time_frames]
        self.exchange_manager.time_frames = self.config_time_frames

        self.time_frame_get_times = {}
        self.time_frames_offset = {}

        self.DEFAULT_LIMIT = 100
        self.MIN_LIMIT = 30

        # used to force price movement
        self.recent_trades_multiplier_factor = 1

        self.MIN_ENABLED_TIME_FRAME = TimeFrameManager.find_min_time_frame(self.config_time_frames)
        self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR = self.MIN_ENABLED_TIME_FRAME
        self.DEFAULT_TIME_FRAME_TICKERS_CREATOR = self.MIN_ENABLED_TIME_FRAME
        self.RECENT_TRADES_TO_CREATE = max(SIMULATOR_LAST_PRICES_TO_CHECK, ORDER_CREATION_LAST_TRADES_TO_USE)

        self.backtesting = Backtesting(self.config, self)
        self._prepare()

    def get_symbol_data(self, symbol):
        return self.exchange_manager.get_symbol_data(symbol)

    def get_personal_data(self):
        return self.exchange_manager.get_exchange_personal_data()

    # todo merge multiple file with the same symbol
    def _get_symbol_list(self):
        self.symbols = []
        self.data = {}
        symbols_appended = {}

        # parse files
        for file in self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES]:
            exchange_name, symbol, timestamp = ExchangeDataCollector.get_file_name(file)
            if exchange_name is not None and symbol is not None and timestamp is not None:

                # check if symbol data already in symbols
                # TODO check exchanges ?
                if symbol not in symbols_appended:
                    symbols_appended[symbol] = 0
                    if symbols_appended[symbol] < int(timestamp):
                        symbols_appended[symbol] = int(timestamp)
                        self.symbols.append(symbol)
                        data = DataCollectorParser.parse(file)
                        self.data[symbol] = self.fix_timestamps(data)

    @staticmethod
    def need_transform_timeframes(timeframes):
        if timeframes:
            try:
                datetime.datetime.fromtimestamp(timeframes)
            except OSError:
                return True
            except ValueError:
                return True
        return False

    def fix_timestamps(self, data):
        if get_bot() is not None:
            for time_frame in data:
                need_to_uniform_timestamps = ExchangeSimulator.need_transform_timeframes(
                    data[time_frame][0][PriceIndexes.IND_PRICE_TIME.value])
                for data_list in data[time_frame]:
                    if need_to_uniform_timestamps:
                        data_list[PriceIndexes.IND_PRICE_TIME.value] = \
                            self.get_uniform_timestamp(data_list[PriceIndexes.IND_PRICE_TIME.value])
        return data

    # returns price data for a given symbol
    def _get_symbol_data(self, symbol):
        return self.data[symbol]

    def symbol_exists(self, symbol):
        return symbol in self.symbols

    def time_frame_exists(self, time_frame):
        return time_frame in self.time_frame_get_times

    def has_data_for_time_frame(self, symbol, time_frame):
        return time_frame in self.data[symbol] \
               and len(self.data[symbol][time_frame]) >= self.DEFAULT_LIMIT + self.MIN_LIMIT

    def get_symbols(self):
        return self.symbols

    def get_name(self):
        return self.__class__.__name__ + str(self.symbols)

    def _prepare(self):
        # create get times and init offsets
        for time_frame in TimeFrames:
            self.time_frame_get_times[time_frame.value] = 0
            self.time_frames_offset = {}

    def should_update_data(self, time_frame):
        smallest_time_frame = TimeFrameManager.find_min_time_frame(self.config_time_frames)
        if smallest_time_frame == time_frame:
            # always True: refresh smallest timeframe systematically when possible
            return True
        else:
            smallest_time_frame_sec = TimeFramesMinutes[smallest_time_frame]
            smallest_time_frame_updated_times = self.time_frame_get_times[smallest_time_frame.value]
            # - 1 because smallest timeframe is the 1st to be updated: always return true for it but others need not to
            # be biased by the previous + 1 from current timeframe update wave
            smallest_time_frame_updated_times_to_compare = smallest_time_frame_updated_times - 1 \
                if smallest_time_frame_updated_times > 0 else 0
            current_time_frame_sec = TimeFramesMinutes[time_frame]
            current_time_frame_updated_times = self.time_frame_get_times[time_frame.value]

            time_refresh_condition = (smallest_time_frame_updated_times_to_compare - (
                    current_time_frame_updated_times * (current_time_frame_sec / smallest_time_frame_sec)) >= 0)

            return time_refresh_condition

    # Will use the One Minute time frame
    def _create_ticker(self, symbol, index):
        tf = self._get_symbol_data(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value][index]
        return tf[PriceIndexes.IND_PRICE_CLOSE.value]

    def _create_recent_trades(self, symbol, timeframe, index):
        tf = self._get_symbol_data(symbol)[timeframe.value][index]
        trades = []
        created_trades = []

        max_price = tf[PriceIndexes.IND_PRICE_HIGH.value]
        min_price = tf[PriceIndexes.IND_PRICE_LOW.value]

        # TODO generate trades with different patterns (linear, waves, random, etc)
        for _ in range(0, self.RECENT_TRADES_TO_CREATE - 2):
            trades.append((max_price + min_price) / 2)

        # add very max and very min
        trades.append(max_price)
        trades.append(min_price)

        for trade in trades:
            created_trades.append(
                {
                    "price": trade*self.recent_trades_multiplier_factor,
                    "timestamp": time.time()
                }
            )

        return created_trades

    def _extract_from_indexes(self, array, max_index, factor=1):
        max_limit = len(array)
        max_index *= factor

        if max_index > max_limit:
            self.backtesting.end()

        else:
            return array[:max_index]

    def _get_candle_index(self, timeframe, symbol):
        if symbol not in self.data or timeframe not in self.data[symbol]:
            self.logger.error("get_candle_index(self, timeframe, symbol) called with unset "
                              f"time_frames_offset[symbol][timeframe] for symbol: {symbol} and  timeframe: {timeframe}."
                              " Call init_candles_offset(self, timeframes, symbol) to set candles indexes in order to "
                              "have consistent candles on different timeframes while using the timeframes you are "
                              "interested in")
        return self.time_frames_offset[symbol][timeframe] + self.time_frame_get_times[timeframe]

    def _extract_data_with_limit(self, symbol, time_frame):
        to_use_timeframe = time_frame.value if time_frame is not None \
            else TimeFrameManager.find_min_time_frame(self.data[symbol].keys())
        return self._extract_from_indexes(self.data[symbol][to_use_timeframe],
                                          self._get_candle_index(to_use_timeframe, symbol))

    def get_candles_exact(self, symbol, time_frame, min_index, max_index, return_list=True):
        candles = self.data[symbol][time_frame.value][min_index:max_index]
        self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles, replace_all=True)
        return self.get_symbol_data(symbol).get_symbol_prices(time_frame, None, return_list)

    def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        candles = self._extract_data_with_limit(symbol, time_frame)
        if time_frame is not None:
            self.time_frame_get_times[time_frame.value] += 1
        self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles, replace_all=True)

    def _get_used_timeframes(self, symbol):
        if symbol in self.time_frames_offset:
            return self.time_frames_offset[symbol].keys()
        else:
            return [self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR]

    def get_recent_trades(self, symbol, limit=50):
        timeframe_to_use = TimeFrameManager.find_min_time_frame(self._get_used_timeframes(symbol))
        index = 0
        if symbol in self.time_frames_offset and timeframe_to_use.value in self.time_frames_offset[symbol] \
           and timeframe_to_use.value in self.time_frame_get_times:
            # -2 because take into account the +1 in self.time_frame_get_times and the fact that it's an index
            index = self.time_frames_offset[symbol][timeframe_to_use.value] \
                    + self.time_frame_get_times[timeframe_to_use.value] \
                    - 2
        trades = self._create_recent_trades(
            symbol, timeframe_to_use,
            index
        )
        self.get_symbol_data(symbol).update_recent_trades(trades)

    def _find_min_timeframe_to_consider(self, timeframes, symbol):
        timeframes_to_consider = copy.copy(timeframes)
        min_timeframe_to_consider = None
        while not min_timeframe_to_consider and timeframes_to_consider:
            potential_min_timeframe_to_consider = TimeFrameManager.find_min_time_frame(timeframes_to_consider).value
            if potential_min_timeframe_to_consider in self.data[symbol]:
                min_timeframe_to_consider = potential_min_timeframe_to_consider
            else:
                timeframes_to_consider.remove(potential_min_timeframe_to_consider)
        if min_timeframe_to_consider:
            return self.data[symbol][min_timeframe_to_consider][self.MIN_LIMIT][PriceIndexes.IND_PRICE_TIME.value]
        else:
            self.logger.error(f"No data for the timeframes: {timeframes} in loaded backtesting file.")
            if Backtesting.enabled(self.config):
                self.backtesting.end()

    """
    Used to set self.time_frames_offset: will set offsets for all the given timeframes to keep data consistent 
    relatively to the smallest timeframe given in timeframes list.
    Ex: timeframes = ["1m", "1h", "1d"] => this will set offsets at 0 for "1m" because it is the smallest timeframe and
    will find the corresponding offset for the "1h" and "1d" timeframes if associated data are going further in the past
    than the "1m" timeframe. 
    This is used to avoid data from 500 hours ago mixed with data from 500 min ago for example.
    """

    def init_candles_offset(self, timeframes, symbol):
        min_timeframe_to_consider = self._find_min_timeframe_to_consider(timeframes, symbol)
        if symbol not in self.time_frames_offset:
            self.time_frames_offset[symbol] = {}
        for timeframe in timeframes:
            if timeframe.value in self.data[symbol]:
                found_index = False
                for index, candle in enumerate(self.data[symbol][timeframe.value]):
                    if candle[PriceIndexes.IND_PRICE_TIME.value] >= min_timeframe_to_consider:
                        found_index = True
                        self.time_frames_offset[symbol][timeframe.value] = index
                        break
                if not found_index:
                    self.time_frames_offset[symbol][timeframe.value] = len(self.data[symbol][timeframe.value]) - 1

    def get_data(self):
        return self.data

    def get_price_ticker(self, symbol):
        result = {
            "symbol": symbol,
            ExchangeConstantsTickersColumns.LAST.value: self._create_ticker(
                symbol,
                self.time_frame_get_times[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value])
        }
        self.get_symbol_data(symbol).update_symbol_ticker(result)

    def get_last_price_ticker(self, symbol):
        return self.get_price_ticker(symbol)[ExchangeConstantsTickersColumns.LAST.value]

    def get_all_currencies_price_ticker(self):
        return {
            symbol: {
                "symbol": symbol,
                ExchangeConstantsTickersColumns.LAST.value: self.get_price_ticker(symbol)
            }
            for symbol in self.symbols
        }

    def get_market_status(self, symbol):
        return {
            # fees
            ExchangeConstantsMarketStatusColumns.TAKER.value: 0.001,
            ExchangeConstantsMarketStatusColumns.MAKER.value: 0.001,
            # number of decimal digits "after the dot"
            ExchangeConstantsMarketStatusColumns.PRECISION.value: {
                ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 8,
                ExchangeConstantsMarketStatusColumns.PRECISION_COST.value: 8,
                ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 8,
            },
            ExchangeConstantsMarketStatusColumns.LIMITS.value: {
                ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.00001,
                    ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 1000000000000,
                },
                ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 0.00001,
                    ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000000000000,
                },
                ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.001,
                    ExchangeConstantsMarketStatusColumns.LIMITS_COST_MAX.value: 1000000000000,
                },
            },
        }

    def set_recent_trades_multiplier_factor(self, factor):
        self.recent_trades_multiplier_factor = factor

    # Unimplemented methods from AbstractExchange
    def cancel_order(self, order_id, symbol=None):
        return True

    def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        pass

    def get_all_orders(self, symbol=None, since=None, limit=None):
        return []

    def get_balance(self):
        return None

    def get_closed_orders(self, symbol=None, since=None, limit=None):
        return []

    def get_market_price(self, symbol):
        raise NotImplementedError("get_market_price not implemented")

    def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return []

    def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        return []

    def get_order(self, order_id, symbol=None):
        raise NotImplementedError("get_order not implemented")

    def get_order_book(self, symbol, limit=30):
        raise NotImplementedError("get_order_book not implemented")

    def get_uniform_timestamp(self, timestamp):
        return timestamp / 1000
