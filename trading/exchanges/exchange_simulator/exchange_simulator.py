#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import copy
import time

from backtesting import BacktestingEndedException, backtesting_enabled
from backtesting.backtesting import Backtesting
from backtesting.collector.data_file_manager import interpret_file_name
from backtesting.collector.data_parser import DataCollectorParser
from config import TimeFrames, ExchangeConstantsMarketStatusColumns, CONFIG_BACKTESTING, \
    SIMULATOR_LAST_PRICES_TO_CHECK, ORDER_CREATION_LAST_TRADES_TO_USE, CONFIG_BACKTESTING_DATA_FILES, PriceIndexes, \
    TimeFramesMinutes, ExchangeConstantsTickersColumns, CONFIG_SIMULATOR, CONFIG_SIMULATOR_FEES, \
    CONFIG_SIMULATOR_FEES_MAKER, CONFIG_DEFAULT_SIMULATOR_FEES, TraderOrderType, FeePropertyColumns, \
    ExchangeConstantsMarketPropertyColumns, CONFIG_SIMULATOR_FEES_TAKER, CONFIG_SIMULATOR_FEES_WITHDRAW, \
    BACKTESTING_DATA_OHLCV, BACKTESTING_DATA_TRADES, ExchangeConstantsOrderColumns, OHLCVStrings
from tools.time_frame_manager import TimeFrameManager
from tools.symbol_util import split_symbol
from tools.data_util import DataUtil
from tools.number_util import round_into_str_with_max_digits
from tools.config_manager import ConfigManager
from trading import AbstractExchange
from trading.exchanges.exchange_symbol_data import SymbolData


class ExchangeSimulator(AbstractExchange):
    def __init__(self, config, exchange_type, exchange_manager):
        super().__init__(config, exchange_type)
        self.initializing = True
        self.exchange_manager = exchange_manager

        if CONFIG_BACKTESTING not in self.config:
            raise Exception("Backtesting config not found")

        self.symbols = None
        self.data = None
        self._get_symbol_list()

        self.config_time_frames = TimeFrameManager.get_config_time_frame(self.config)

        # set exchange manager attributes
        self.exchange_manager.client_symbols = self.symbols
        self.exchange_manager.client_time_frames = self.get_available_timeframes()
        self.exchange_manager.time_frames = self.config_time_frames

        self.time_frame_get_times = {}
        self.time_frames_offset = {}
        self.min_time_frame_to_consider = {}

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
        self.initializing = False

    def get_available_timeframes(self):
        client_timeframes = {}
        for symbol in self.symbols:
            client_timeframes[symbol] = [tf.value
                                         for tf in self.config_time_frames
                                         if tf.value in self.get_ohlcv(symbol)]
        return client_timeframes

    def get_symbol_data(self, symbol):
        return self.exchange_manager.get_symbol_data(symbol)

    def get_personal_data(self):
        return self.exchange_manager.get_exchange_personal_data()

    # todo merge multiple file with the same symbol
    def _get_symbol_list(self):
        self.symbols = []
        self.data = {}
        symbols_appended = {}
        relevant_symbols = set(ConfigManager.get_symbols(self.config))

        # parse files
        for file in self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES]:
            exchange_name, symbol, timestamp, data_type = interpret_file_name(file)
            if symbol is not None and symbol in relevant_symbols:
                if exchange_name is not None and timestamp is not None and data_type is not None:

                    # check if symbol data already in symbols
                    # TODO check exchanges ?
                    if symbol not in symbols_appended:
                        symbols_appended[symbol] = 0
                        if symbols_appended[symbol] < int(timestamp):
                            symbols_appended[symbol] = int(timestamp)
                            self.symbols.append(symbol)
                            data = DataCollectorParser.parse(file)
                            self.data[symbol] = self.fix_timestamps(data)

    def fix_timestamps(self, data):
        for time_frame in data[BACKTESTING_DATA_OHLCV]:
            need_to_uniform_timestamps = self.exchange_manager.need_to_uniformize_timestamp(
                data[BACKTESTING_DATA_OHLCV][time_frame][0][PriceIndexes.IND_PRICE_TIME.value])
            for data_list in data[BACKTESTING_DATA_OHLCV][time_frame]:
                if need_to_uniform_timestamps:
                    data_list[PriceIndexes.IND_PRICE_TIME.value] = \
                        self.get_uniform_timestamp(data_list[PriceIndexes.IND_PRICE_TIME.value])
        return data

    # returns price (ohlcv) data for a given symbol
    def get_ohlcv(self, symbol):
        return self.data[symbol][BACKTESTING_DATA_OHLCV]

    # returns trades data for a given symbol
    def get_trades(self, symbol):
        return self.data[symbol][BACKTESTING_DATA_TRADES]

    def handles_trades_history(self, symbol):
        return self.get_trades(symbol)

    def symbol_exists(self, symbol):
        return symbol in self.symbols

    def time_frame_exists(self, time_frame):
        return time_frame in self.time_frame_get_times

    def has_data_for_time_frame(self, symbol, time_frame):
        return time_frame in self.get_ohlcv(symbol) \
               and len(self.get_ohlcv(symbol)[time_frame]) >= self.DEFAULT_LIMIT + self.MIN_LIMIT

    def get_symbols(self):
        return self.symbols

    def get_name(self):
        return self.__class__.__name__ + str(self.symbols)

    def _prepare(self):
        # create get times and init offsets
        for symbol in self.symbols:
            self.time_frame_get_times[symbol] = {}
            for time_frame in TimeFrames:
                self.time_frame_get_times[symbol][time_frame.value] = 0
                self.time_frames_offset = {}

    def should_update_data(self, time_frame, symbol):
        smallest_time_frame = TimeFrameManager.find_min_time_frame(self.config_time_frames)
        if smallest_time_frame == time_frame:
            # always True: refresh smallest timeframe systematically when possible
            return True
        else:
            smallest_time_frame_sec = TimeFramesMinutes[smallest_time_frame]
            try:
                smallest_time_frame_timestamp = self._get_current_timestamp(smallest_time_frame, symbol, 1)
                wanted_time_frame_timestamp = self._get_current_timestamp(time_frame, symbol)

                return wanted_time_frame_timestamp <= smallest_time_frame_timestamp + (smallest_time_frame_sec / 2)
            except IndexError:
                return False

    def _get_current_timestamp(self, time_frame, symbol, backwards=0):
        time_frame_index = self._get_candle_index(time_frame.value, symbol)
        if time_frame_index - backwards > 0:
            time_frame_index = time_frame_index - backwards
        return self.get_ohlcv(symbol)[time_frame.value][time_frame_index][PriceIndexes.IND_PRICE_TIME.value]

    # Will use the One Minute time frame
    def _create_ticker(self, symbol, index):
        if self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value in self.get_ohlcv(symbol):
            nb_candles = len(self.get_ohlcv(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value])
            if index >= nb_candles:
                tf = self.get_ohlcv(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value][-1]
                self.logger.warning(f"Impossible to simulate price ticker for {symbol} at candle index {index} "
                                    f"(only {nb_candles} candles are available). "
                                    f"Creating ticker using the last available candle.")
            else:
                tf = self.get_ohlcv(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value][index]
            return tf[PriceIndexes.IND_PRICE_CLOSE.value]
        else:
            raise NoCandleDataForThisTimeFrameException(
                f"No candle data for {self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value} time frame for {symbol}.")

    def _fetch_recent_trades(self, symbol, timeframe, index):
        time_frame = self.get_ohlcv(symbol)[timeframe.value][index]
        start_timestamp = time_frame[PriceIndexes.IND_PRICE_TIME.value] \
            if backtesting_enabled(self.config) else time.time()

        if not self.handles_trades_history(symbol) or not backtesting_enabled(self.config):
            return self.generate_trades(time_frame, start_timestamp)
        else:
            end_timestamp = self.get_ohlcv(symbol)[timeframe.value][index+1][PriceIndexes.IND_PRICE_TIME.value] \
                if len(self.get_ohlcv(symbol)[timeframe.value]) > index+1 else -1
            return self.select_trades(start_timestamp, end_timestamp, symbol)

    def select_trades(self, start_timestamp, end_timestamp, symbol):
        trades = self.get_trades(symbol)
        current_trades = [trade for trade in trades
                          if (self.get_uniform_timestamp(trade[ExchangeConstantsOrderColumns.TIMESTAMP.value])
                              >= start_timestamp
                              and (self.get_uniform_timestamp(trade[ExchangeConstantsOrderColumns.TIMESTAMP.value])
                                   <= end_timestamp
                                   or end_timestamp == -1))
                          ]
        return [{
                    "price": float(trade_dict[ExchangeConstantsOrderColumns.PRICE.value]),
                    "timestamp": self.get_uniform_timestamp(trade_dict[ExchangeConstantsOrderColumns.TIMESTAMP.value])
                } for trade_dict in current_trades]

    def generate_trades(self, time_frame, timestamp):
        trades = []
        created_trades = []
        max_price = time_frame[PriceIndexes.IND_PRICE_HIGH.value]
        min_price = time_frame[PriceIndexes.IND_PRICE_LOW.value]
        # TODO generate trades with different patterns (linear, waves, random, etc)
        for _ in range(0, self.RECENT_TRADES_TO_CREATE - 2):
            trades.append((max_price + min_price) / 2)

        # add very max and very min
        trades.append(max_price)
        trades.append(min_price)

        for trade in trades:
            created_trades.append(
                {
                    "price": trade * self.recent_trades_multiplier_factor,
                    "timestamp": timestamp
                }
            )

        return created_trades

    @staticmethod
    def _extract_from_indexes(array, max_index, symbol, factor=1):
        max_limit = len(array)
        max_index *= factor

        if max_index > max_limit:
            raise BacktestingEndedException(symbol)

        else:
            return array[:max_index]

    def _get_candle_index(self, time_frame, symbol):
        if symbol not in self.data or time_frame not in self.get_ohlcv(symbol):
            self.logger.error("get_candle_index(self, timeframe, symbol) called with unset "
                              f"time_frames_offset[symbol][timeframe] for symbol: {symbol} and timeframe: {time_frame}."
                              " Call init_candles_offset(self, timeframes, symbol) to set candles indexes in order to "
                              "have consistent candles on different timeframes while using the timeframes you are "
                              "interested in")
        return self.time_frames_offset[symbol][time_frame] + self.time_frame_get_times[symbol][time_frame]

    def _extract_data_with_limit(self, symbol, time_frame):
        to_use_time_frame = time_frame.value or \
                            TimeFrameManager.find_min_time_frame(self.time_frames_offset[symbol].keys()).value
        return self._extract_from_indexes(self.get_ohlcv(symbol)[to_use_time_frame],
                                          self._get_candle_index(to_use_time_frame, symbol),
                                          symbol)

    def _ensure_available_data(self, symbol):
        if symbol not in self.data:
            raise NoCandleDataForThisSymbolException(f"No candles data for {symbol} symbol.")

    def get_candles_exact(self, symbol, time_frame, min_index, max_index, return_list=True):
        self._ensure_available_data(symbol)
        candles = self.get_ohlcv(symbol)[time_frame.value][min_index:max_index]
        self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles, replace_all=True)
        return self.get_symbol_data(symbol).get_symbol_prices(time_frame, None, return_list)

    async def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        self._ensure_available_data(symbol)
        candles = self._extract_data_with_limit(symbol, time_frame)
        if time_frame is not None:
            self.time_frame_get_times[symbol][time_frame.value] += 1
            # if it's at least the second iteration: only use the last candle, otherwise use all
            if self.time_frame_get_times[symbol][time_frame.value] > 1:
                candles = candles[-1]
            self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles)

    def get_full_candles_data(self, symbol, time_frame):
        full_data = self.get_ohlcv(symbol)[time_frame.value]
        temp_symbol_data = SymbolData(symbol)
        temp_symbol_data.update_symbol_candles(time_frame, full_data, True)
        return temp_symbol_data.get_symbol_prices(time_frame)

    def _get_used_time_frames(self, symbol):
        if symbol in self.time_frames_offset:
            return self.time_frames_offset[symbol].keys()
        else:
            return [self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR]

    async def get_recent_trades(self, symbol, limit=50):
        self._ensure_available_data(symbol)
        time_frame_to_use = TimeFrameManager.find_min_time_frame(self._get_used_time_frames(symbol))
        index = 0
        if symbol in self.time_frames_offset and time_frame_to_use.value in self.time_frames_offset[symbol] \
                and time_frame_to_use.value in self.time_frame_get_times[symbol]:
            # -2 because take into account the +1 in self.time_frame_get_times and the fact that it's an index
            index = self.time_frames_offset[symbol][time_frame_to_use.value] \
                    + self.time_frame_get_times[symbol][time_frame_to_use.value] \
                    - 2
        trades = self._fetch_recent_trades(
            symbol, time_frame_to_use,
            index
        )
        self.get_symbol_data(symbol).update_recent_trades(trades)

    def _find_min_time_frame_to_consider(self, time_frames, symbol):
        time_frames_to_consider = copy.copy(time_frames)
        self.min_time_frame_to_consider[symbol] = None
        while not self.min_time_frame_to_consider[symbol] and time_frames_to_consider:
            potential_min_time_frame_to_consider = TimeFrameManager.find_min_time_frame(time_frames_to_consider).value
            if potential_min_time_frame_to_consider in self.get_ohlcv(symbol):
                self.min_time_frame_to_consider[symbol] = potential_min_time_frame_to_consider
            else:
                time_frames_to_consider.remove(potential_min_time_frame_to_consider)
        if self.min_time_frame_to_consider[symbol]:
            return self.get_ohlcv(symbol)[self.min_time_frame_to_consider[symbol]][self.MIN_LIMIT] \
                [PriceIndexes.IND_PRICE_TIME.value]
        else:
            self.logger.error(f"No data for the timeframes: {time_frames} in loaded backtesting file.")
            if backtesting_enabled(self.config):
                self.backtesting.end(symbol)

    """
    Used to set self.time_frames_offset: will set offsets for all the given timeframes to keep data consistent 
    relatively to the smallest timeframe given in timeframes list.
    Ex: timeframes = ["1m", "1h", "1d"] => this will set offsets at 0 for "1m" because it is the smallest timeframe and
    will find the corresponding offset for the "1h" and "1d" timeframes if associated data are going further in the past
    than the "1m" timeframe. 
    This is used to avoid data from 500 hours ago mixed with data from 500 min ago for example.
    """

    def init_candles_offset(self, time_frames, symbol):
        min_time_frame_to_consider = dict()
        min_time_frame_to_consider[symbol] = self._find_min_time_frame_to_consider(time_frames, symbol)
        if symbol not in self.time_frames_offset:
            self.time_frames_offset[symbol] = {}
        for time_frame in time_frames:
            if time_frame.value in self.get_ohlcv(symbol):
                found_index = False
                for index, candle in enumerate(self.get_ohlcv(symbol)[time_frame.value]):
                    if candle[PriceIndexes.IND_PRICE_TIME.value] >= min_time_frame_to_consider[symbol]:
                        index_to_use = index
                        if candle[PriceIndexes.IND_PRICE_TIME.value] > min_time_frame_to_consider[symbol] and \
                                index > 0:
                            # if superior: take the prvious one
                            index_to_use = index - 1
                        found_index = True
                        self.time_frames_offset[symbol][time_frame.value] = index_to_use
                        break
                if not found_index:
                    self.time_frames_offset[symbol][time_frame.value] = \
                        len(self.get_ohlcv(symbol)[time_frame.value]) - 1

    def get_min_time_frame(self, symbol):
        if symbol in self.min_time_frame_to_consider:
            return self.min_time_frame_to_consider[symbol]
        else:
            return None

    def get_progress(self):
        if not self.min_time_frame_to_consider:
            return 0
        else:
            progresses = []
            for symbol in self.time_frame_get_times:
                if symbol in self.min_time_frame_to_consider:
                    current = self.time_frame_get_times[symbol][self.min_time_frame_to_consider[symbol]]
                    nb_max = len(self.get_ohlcv(symbol)[self.min_time_frame_to_consider[symbol]])
                    progresses.append(current / nb_max)
            return int(DataUtil.mean(progresses) * 100)

    async def get_price_ticker(self, symbol):
        self._ensure_available_data(symbol)
        result = {
            "symbol": symbol,
            ExchangeConstantsTickersColumns.LAST.value: self._create_ticker(
                symbol,
                self.time_frame_get_times[symbol][self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value])
        }
        self.get_symbol_data(symbol).update_symbol_ticker(result)

    async def get_last_price_ticker(self, symbol):
        ticker = await self.get_price_ticker(symbol)
        return ticker[ExchangeConstantsTickersColumns.LAST.value]

    async def get_all_currencies_price_ticker(self):
        return {
            symbol: {
                "symbol": symbol,
                ExchangeConstantsTickersColumns.LAST.value: await self.get_price_ticker(symbol)
            }
            for symbol in self.symbols
        }

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        return {
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

    async def end_backtesting(self, symbol):
        await self.backtesting.end(symbol)

    def set_recent_trades_multiplier_factor(self, factor):
        self.recent_trades_multiplier_factor = factor

    # Unimplemented methods from AbstractExchange
    async def cancel_order(self, order_id, symbol=None):
        return True

    async def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        pass

    async def get_all_orders(self, symbol=None, since=None, limit=None):
        return []

    async def get_balance(self):
        return None

    async def get_closed_orders(self, symbol=None, since=None, limit=None):
        return []

    async def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return []

    async def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        return []

    async def get_order(self, order_id, symbol=None):
        raise NotImplementedError("get_order not implemented")

    async def get_order_book(self, symbol, limit=30):
        raise NotImplementedError("get_order_book not implemented")

    async def stop(self):
        pass

    def get_uniform_timestamp(self, timestamp):
        return timestamp / 1000

    def get_backtesting(self):
        return self.backtesting

    def get_is_initializing(self):
        return self.initializing

    def get_fees(self, symbol=None):
        result_fees = {
            ExchangeConstantsMarketPropertyColumns.TAKER.value: CONFIG_DEFAULT_SIMULATOR_FEES,
            ExchangeConstantsMarketPropertyColumns.MAKER.value: CONFIG_DEFAULT_SIMULATOR_FEES,
            ExchangeConstantsMarketPropertyColumns.FEE.value: CONFIG_DEFAULT_SIMULATOR_FEES
        }

        if CONFIG_SIMULATOR in self.config and CONFIG_SIMULATOR_FEES in self.config[CONFIG_SIMULATOR]:
            if CONFIG_SIMULATOR_FEES_MAKER in self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES]:
                result_fees[ExchangeConstantsMarketPropertyColumns.MAKER.value] = \
                    self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES][CONFIG_SIMULATOR_FEES_MAKER]

            if CONFIG_SIMULATOR_FEES_MAKER in self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES]:
                result_fees[ExchangeConstantsMarketPropertyColumns.TAKER.value] = \
                    self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES][CONFIG_SIMULATOR_FEES_TAKER]

            if CONFIG_SIMULATOR_FEES_WITHDRAW in self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES]:
                result_fees[ExchangeConstantsMarketPropertyColumns.FEE.value] = \
                    self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES][CONFIG_SIMULATOR_FEES_WITHDRAW]

        return result_fees

    # returns {
    #     'type': takerOrMaker,
    #     'currency': 'BTC', // the unified fee currency code
    #     'rate': percentage, // the fee rate, 0.05% = 0.0005, 1% = 0.01, ...
    #     'cost': feePaid, // the fee cost (amount * fee rate)
    # }
    def get_trade_fee(self, symbol, order_type, quantity, price,
                      taker_or_maker=ExchangeConstantsMarketPropertyColumns.TAKER.value):
        symbol_fees = self.get_fees(symbol)
        rate = symbol_fees[taker_or_maker] / 100  # /100 because rate in used in %
        currency, market = split_symbol(symbol)
        fee_currency = currency

        precision = self.get_market_status(symbol)[ExchangeConstantsMarketStatusColumns.PRECISION.value] \
            [ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value]
        cost = float(round_into_str_with_max_digits(quantity * rate, precision))

        if order_type == TraderOrderType.SELL_MARKET or order_type == TraderOrderType.SELL_LIMIT:
            cost = float(round_into_str_with_max_digits(cost * price, precision))
            fee_currency = market

        return {
            FeePropertyColumns.TYPE.value: taker_or_maker,
            FeePropertyColumns.CURRENCY.value: fee_currency,
            FeePropertyColumns.RATE.value: rate,
            FeePropertyColumns.COST.value: cost
        }


class NoCandleDataForThisTimeFrameException(Exception):
    pass


class NoCandleDataForThisSymbolException(Exception):
    pass
