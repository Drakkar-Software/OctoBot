from backtesting import get_bot
from backtesting.backtesting import Backtesting
from backtesting.collector.data_collector import DataCollectorParser
from config.cst import *
from tools.time_frame_manager import TimeFrameManager
from trading import Exchange


class ExchangeSimulator(Exchange):
    def __init__(self, config, exchange_type):
        self.config = config

        if CONFIG_BACKTESTING not in self.config:
            raise Exception("Backtesting config not found")

        if CONFIG_DATA_COLLECTOR not in self.config:
            raise Exception("Data collector config not found")

        self.data = DataCollectorParser.parse(self.config[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILE])
        self.fix_timestamps()

        self.symbols = self._get_symbol_list()

        self.config_time_frames = TimeFrameManager.get_config_time_frame(config)

        self.time_frame_get_times = {}
        self.tickers = {}
        self.fetched_trades = {}
        self.fetched_trades_counter = {}

        self.DEFAULT_LIMIT = 100
        self.MIN_LIMIT = 20

        self.MIN_ENABLED_TIME_FRAME = TimeFrameManager.find_config_min_time_frame(self.config_time_frames)
        self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR = self.MIN_ENABLED_TIME_FRAME
        self.CREATED_TRADES_BY_TIME_FRAME = 50
        self.DEFAULT_TIME_FRAME_TICKERS_CREATOR = self.MIN_ENABLED_TIME_FRAME
        self.CREATED_TICKER_BY_TIME_FRAME = 1

        self.backtesting = Backtesting(config, self)
        self._prepare()

        super().__init__(config, exchange_type, connect_to_online_exchange=False)

    # toto: faire une vrai implémentation lorsque la liste des symboles sera géré définitivement
    def _get_symbol_list(self):
        # temp
        return [self.config[CONFIG_DATA_COLLECTOR][CONFIG_SYMBOL]]

    def fix_timestamps(self):
        if get_bot() is not None:
            for time_frame in self.data:
                time_delta = get_bot().get_start_time()*1000 - self.data[time_frame][0][PriceIndexes.IND_PRICE_TIME.value]
                for data_list in self.data[time_frame]:
                    data_list[PriceIndexes.IND_PRICE_TIME.value] += time_delta

    # returns price data for a given symbol
    def _get_symbol_data(self, symbol):
        # temp: to adapt when multi symbol file is up or any other solution
        # currently 1 symbol per file and 1 file parsed => juste return data
        return self.data

    def symbol_exists(self, symbol):
        return symbol in self.symbols

    def time_frame_exists(self, time_frame):
        return time_frame in self.time_frame_get_times

    def has_data_for_time_frame(self, time_frame):
        return time_frame in self.data \
               and len(self.data[time_frame]) >= self.DEFAULT_LIMIT + self.MIN_LIMIT

    def get_name(self):
        return self.__class__.__name__+str(self.symbols)

    def _prepare(self):

        for symbol in self.symbols:
            # create symbol tickers
            self.tickers[symbol] = self._create_tickers(symbol)

            # create symbol last trades
            self.fetched_trades[symbol] = self._create_recent_trades(symbol)
            self.fetched_trades_counter[symbol] = 0

        # create get times
        for time_frame in TimeFrames:
            self.time_frame_get_times[time_frame.value] = 0

    def should_update_data(self, time_frame):
        previous_time_frame = TimeFrameManager.get_previous_time_frame(self.config_time_frames, time_frame, time_frame)
        previous_time_frame_sec = TimeFramesMinutes[previous_time_frame]
        previous_time_frame_updated_times = self.time_frame_get_times[previous_time_frame.value]
        current_time_frame_sec = TimeFramesMinutes[time_frame]
        current_time_frame_updated_times = self.time_frame_get_times[time_frame.value]

        if previous_time_frame_updated_times - (
                current_time_frame_updated_times * (current_time_frame_sec / previous_time_frame_sec)) >= 0:
            return True
        else:
            return False

    def should_update_recent_trades(self, symbol):
        if symbol in self.fetched_trades_counter:
            if self.fetched_trades_counter[symbol] < self.time_frame_get_times[self.MIN_ENABLED_TIME_FRAME.value]:
                self.fetched_trades_counter[symbol] += 1
                return True
        return False

    def get_symbol_prices(self, symbol, time_frame, limit=None, data_frame=True):
        result = self._extract_data_with_limit(time_frame)
        self.time_frame_get_times[time_frame.value] += 1

        if data_frame:
            return self.candles_array_to_data_frame(result)
        else:
            return result

    # Will use the One Minute time frame
    def _create_tickers(self, symbol):
        full = self._get_symbol_data(symbol)[self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value]
        created_tickers = []
        for tf in full:
            max_price = max(tf[PriceIndexes.IND_PRICE_OPEN.value], tf[PriceIndexes.IND_PRICE_CLOSE.value])
            min_price = min(tf[PriceIndexes.IND_PRICE_OPEN.value], tf[PriceIndexes.IND_PRICE_CLOSE.value])

            created_tickers += self._create_prices_in_range(min_price, max_price, self.CREATED_TRADES_BY_TIME_FRAME)
        return created_tickers

    def _create_recent_trades(self, symbol):
        full = self._get_symbol_data(symbol)[self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR.value]
        created_trades = []
        for tf in full:
            max_price = max(tf[PriceIndexes.IND_PRICE_OPEN.value], tf[PriceIndexes.IND_PRICE_CLOSE.value])
            min_price = min(tf[PriceIndexes.IND_PRICE_OPEN.value], tf[PriceIndexes.IND_PRICE_CLOSE.value])

            trades = self._create_prices_in_range(min_price, max_price, self.CREATED_TRADES_BY_TIME_FRAME)

            for trade in trades:
                created_trades.append(
                    {
                        "price": trade
                    }
                )

        return created_trades

    @staticmethod
    def _create_prices_in_range(min_price, max_price, count):
        diff = max_price - min_price

        if diff == 0:
            return [max_price for _ in range(0, count)]

        generated_prices = []
        inc = diff / count
        for i in range(0, count):
            generated_prices.append(min_price + i*inc)

        return generated_prices

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

    def _extract_data_with_limit(self, time_frame):
        return self._extract_indexes(self.data[time_frame.value], self.time_frame_get_times[time_frame.value])

    def get_recent_trades(self, symbol):
        return self._extract_indexes(self.fetched_trades[symbol],
                                     self.time_frame_get_times[
                                        self.DEFAULT_TIME_FRAME_RECENT_TRADE_CREATOR.value],
                                     factor=self.CREATED_TRADES_BY_TIME_FRAME)

    def get_data(self):
        return self.data

    def get_price_ticker(self, symbol):
        return {
            "symbol": symbol,
            ExchangeConstantsTickersColumns.LAST.value:
                self._extract_indexes(self.tickers[symbol],
                                      self.time_frame_get_times[
                                          self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value],
                                      factor=self.CREATED_TICKER_BY_TIME_FRAME,
                                      max_value=1)[0]
        }

    def get_all_currencies_price_ticker(self):
        return {
            symbol: {
                "symbol": symbol,
                ExchangeConstantsTickersColumns.LAST.value:
                    self._extract_indexes(self.tickers[symbol],
                                          self.time_frame_get_times[
                                             self.DEFAULT_TIME_FRAME_TICKERS_CREATOR.value],
                                          factor=self.CREATED_TICKER_BY_TIME_FRAME,
                                          max_value=1)[0]
            }
            for symbol in self.symbols
        }
