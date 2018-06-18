from backtesting import get_bot
from backtesting.backtesting import Backtesting
from backtesting.collector.data_parser import DataCollectorParser
from backtesting.collector.exchange_collector import ExchangeDataCollector
from config.cst import *
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
        self.fetched_trades_counter = {}

        self.DEFAULT_LIMIT = 100
        self.MIN_LIMIT = 20

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
    def fix_timestamps(data):
        if get_bot() is not None:
            for time_frame in data:
                time_delta = get_bot().get_start_time() * 1000 - data[time_frame][0][PriceIndexes.IND_PRICE_TIME.value]
                for data_list in data[time_frame]:
                    data_list[PriceIndexes.IND_PRICE_TIME.value] += time_delta
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
        # create get times
        for time_frame in TimeFrames:
            self.time_frame_get_times[time_frame.value] = 0

        for symbol in self.symbols:
            # create symbol last trades counter
            self.fetched_trades_counter[symbol] = 0

    def should_update_data(self, symbol, time_frame, trader):
        previous_time_frame = TimeFrameManager.get_previous_time_frame(self.config_time_frames, time_frame, time_frame)
        previous_time_frame_sec = TimeFramesMinutes[previous_time_frame]
        previous_time_frame_updated_times = self.time_frame_get_times[previous_time_frame.value]
        current_time_frame_sec = TimeFramesMinutes[time_frame]
        current_time_frame_updated_times = self.time_frame_get_times[time_frame.value]

        time_refresh_condition = (previous_time_frame_updated_times - (
                current_time_frame_updated_times * (current_time_frame_sec / previous_time_frame_sec)) >= 0)

        recent_trades_condition = trader.get_open_orders() and (
                                  self.fetched_trades_counter[symbol] > current_time_frame_updated_times)

        return time_refresh_condition and (not trader.get_open_orders() or recent_trades_condition)

    def should_update_recent_trades(self, symbol):
        if symbol in self.fetched_trades_counter:
            if self.time_frame_get_times[self.MIN_ENABLED_TIME_FRAME.value] >= self.fetched_trades_counter[symbol]:
                self.fetched_trades_counter[symbol] += 1
                return True
        return False

    # Will use the One Minute time frame
    def _create_ticker(self, symbol, index):
        tf = self._get_symbol_data(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value][index]
        return tf[PriceIndexes.IND_PRICE_CLOSE.value]

    def _create_recent_trades(self, symbol, index):
        tf = self._get_symbol_data(symbol)[self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR.value][index]
        trades = []
        created_trades = []

        max_price = tf[PriceIndexes.IND_PRICE_HIGH.value]
        min_price = tf[PriceIndexes.IND_PRICE_LOW.value]

        for _ in range(0, self.RECENT_TRADES_TO_CREATE - 2):
            trades.append((max_price + min_price) / 2)

        # add very max and very min
        trades.append(max_price)
        trades.append(min_price)

        for trade in trades:
            created_trades.append(
                {
                    "price": trade*self.recent_trades_multiplier_factor
                }
            )

        return created_trades

    def _extract_indexes(self, array, index, factor=1, max_value=None):
        max_limit = len(array)
        index *= factor
        max_count = max_value if max_value is not None else self.DEFAULT_LIMIT
        min_count = max_value if max_value is not None else self.MIN_LIMIT

        if max_limit - (index + max_count) <= min_count:
            self.backtesting.end()

        elif index + max_count >= max_limit:
            return array[index::]
        else:
            return array[index:index + max_count]

    def _extract_data_with_limit(self, symbol, time_frame):
        return self._extract_indexes(self.data[symbol][time_frame.value], self.time_frame_get_times[time_frame.value])

    def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        result = self._extract_data_with_limit(symbol, time_frame)
        self.time_frame_get_times[time_frame.value] += 1
        self.get_symbol_data(symbol).update_symbol_candles(time_frame, result, replace_all=True)

    def get_recent_trades(self, symbol):
        trades = self._create_recent_trades(
            symbol, self.time_frame_get_times[self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR.value])
        self.get_symbol_data(symbol).update_recent_trades(trades)

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
            # number of decimal digits "after the dot"
            ExchangeConstantsMarketStatusColumns.PRECISION.value: {
                ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value: 8,
                ExchangeConstantsMarketStatusColumns.PRECISION_COST.value: 8,
                ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value: 8,
            },
            ExchangeConstantsMarketStatusColumns.LIMITS.value: {
                ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value: 0.00000000001,
                    ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value: 1000000000000,
                },
                ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value: 0.00000000001,
                    ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value: 1000000000000,
                },
                ExchangeConstantsMarketStatusColumns.LIMITS_COST.value: {
                    ExchangeConstantsMarketStatusColumns.LIMITS_COST_MIN.value: 0.00000000001,
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
        return timestamp
