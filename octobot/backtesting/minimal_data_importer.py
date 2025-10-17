import octobot_commons.enums
import octobot_commons.databases as databases
import octobot_commons.constants
import octobot_commons.symbols
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_backtesting.importers
import octobot_backtesting.enums

import octobot_trading.util.test_tools.exchange_data as exchange_data_import


class MinimalDataImporter(octobot_backtesting.importers.ExchangeDataImporter):
    def __init__(self, config, file_path):
        super().__init__(config, file_path)
        self.available_data_types = [octobot_backtesting.enums.ExchangeDataTables.OHLCV]
        self._candles_cache: dict = {}
        self._min_timestamp = None
        self._max_timestamp = None

    def update_from_exchange_data(self, exchange_data: exchange_data_import.ExchangeData):
        self.has_all_time_frames_candles_history = True
        self.exchange_name = exchange_data.exchange_details.name
        self.symbols = sorted(list(set(
            market_details.symbol
            for market_details in exchange_data.markets
            if market_details.has_full_candles()
        )))
        self.time_frames = time_frame_manager.sort_time_frames(list(set(
            octobot_commons.enums.TimeFrames(market_details.time_frame)
            for market_details in exchange_data.markets
            if market_details.has_full_candles()
        )))
        min_timeframe = time_frame_manager.find_min_time_frame(self.time_frames)
        min_timeframe_sec = octobot_commons.enums.TimeFramesMinutes[min_timeframe] \
            * octobot_commons.constants.MINUTE_TO_SECONDS
        # always use the largest dataset for the sample market
        sample_market = self._get_sample_market(exchange_data)
        self._min_timestamp = sample_market.time[0] + min_timeframe_sec
        self._max_timestamp = sample_market.time[-1] + min_timeframe_sec
        self._init_candles_cache(exchange_data)

    def _init_candles_cache(self, exchange_data: exchange_data_import.ExchangeData):
        for market_details in exchange_data.markets:
            if not market_details.has_full_candles():
                continue
            if market_details.time_frame not in self._candles_cache:
                self._candles_cache[market_details.time_frame] = {}
            self._candles_cache[market_details.time_frame][market_details.symbol] = market_details.get_formatted_candles()

    async def initialize(self) -> None:
        # nothing to do
        pass

    async def get_data_timestamp_interval(self, time_frame=None):
        return self._min_timestamp, self._max_timestamp

    async def get_ohlcv(self, exchange_name=None, symbol=None,
                        time_frame=octobot_commons.enums.TimeFrames.ONE_HOUR,
                        limit=databases.SQLiteDatabase.DEFAULT_SIZE,
                        timestamps=None,
                        operations=None):
        return await self._get_from_db(
            exchange_name, symbol, octobot_backtesting.enums.ExchangeDataTables.OHLCV,
            time_frame=time_frame,
            limit=limit,
            timestamps=timestamps,
            operations=operations
        )

    async def _get_from_db(
        self, exchange_name, symbol, table,
        time_frame=None,
        limit=databases.SQLiteDatabase.DEFAULT_SIZE,
        timestamps=None,
        operations=None
    ):
        time_frame = time_frame.value or next(iter(self._candles_cache))
        if timestamps:
            return self._select_from_timestamp(symbol, timestamps, operations, time_frame)

        return self._select(limit, symbol, time_frame)

    def _select_from_timestamp(self, symbol, timestamps, operations, time_frame):
        parsed_timestamps = [float(timestamp) for timestamp in timestamps]
        return [
            candle
            for candle in self._select(databases.SQLiteDatabase.DEFAULT_SIZE, symbol, time_frame)
            if _is_valid_from_operations(
                candle[octobot_commons.enums.PriceIndexes.IND_PRICE_TIME.value], parsed_timestamps, operations
            )
        ]

    def _select(self, limit, symbol, time_frame):
        candles = self._candles_cache[time_frame][symbol]
        timeframe_sec = octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames(time_frame)] * \
            octobot_commons.constants.MINUTE_TO_SECONDS
        currency = octobot_commons.symbols.parse_symbol(symbol).base
        candles_data = [
            [
                candle[octobot_commons.enums.PriceIndexes.IND_PRICE_TIME.value] + timeframe_sec,
                self.exchange_name,
                currency,
                symbol,
                time_frame,
                candle
            ]
            for candle in candles
        ]
        if limit != databases.SQLiteDatabase.DEFAULT_SIZE:
            return candles_data[:limit]
        return candles_data

    @staticmethod
    def _get_sample_market(
        exchange_data: exchange_data_import.ExchangeData
    ) -> exchange_data_import.MarketDetails:
        return sorted(
            [market for market in exchange_data.markets],
            key=lambda m: len(m.time)
        )[-1]


def _is_valid_from_operations(input_timestamp, condition_timestamps, operations):
    for condition_timestamp, operation in zip(condition_timestamps, operations):
        if operation == octobot_commons.enums.DataBaseOperations.SUP.value:
            if not input_timestamp > condition_timestamp:
                return False
        if operation == octobot_commons.enums.DataBaseOperations.SUP_EQUALS.value:
            if not input_timestamp >= condition_timestamp:
                return False
        if operation == octobot_commons.enums.DataBaseOperations.EQUALS.value:
            if not input_timestamp == condition_timestamp:
                return False
        if operation == octobot_commons.enums.DataBaseOperations.INF_EQUALS.value:
            if not input_timestamp <= condition_timestamp:
                return False
        if operation == octobot_commons.enums.DataBaseOperations.INF.value:
            if not input_timestamp < condition_timestamp:
                return False
    return True
