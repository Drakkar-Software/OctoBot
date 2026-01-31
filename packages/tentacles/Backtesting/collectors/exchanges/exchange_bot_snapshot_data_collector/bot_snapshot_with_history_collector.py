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
import asyncio
import copy
import os
import json
import time
import shutil
import collections

import octobot_backtesting.collectors as collector
import octobot_backtesting.importers as importers
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.errors as backtesting_errors
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.databases as databases
import octobot_backtesting.data as data
import octobot_trading.api as trading_api
import octobot_trading.errors as trading_errors
import tentacles.Backtesting.importers.exchanges.generic_exchange_importer as generic_exchange_importer



class ExchangeBotSnapshotWithHistoryCollector(collector.AbstractExchangeBotSnapshotCollector):
    IMPORTER = generic_exchange_importer.GenericExchangeDataImporter
    OHLCV = "ohlcv"
    KLINE = "kline"

    def __init__(self, config, exchange_name, exchange_type, tentacles_setup_config, symbols, time_frames,
                 use_all_available_timeframes=False,
                 data_format=backtesting_enums.DataFormats.REGULAR_COLLECTOR_DATA,
                 start_timestamp=None,
                 end_timestamp=None):
        super().__init__(config, exchange_name, exchange_type, tentacles_setup_config, symbols, time_frames,
                         use_all_available_timeframes, data_format=data_format,
                         start_timestamp=start_timestamp, end_timestamp=end_timestamp)
        self.exchange_type = None
        self.exchange_manager = None
        self.fetch_exchange_manager = None
        self.file_name = data.get_backtesting_file_name(self.__class__,
                                                        self.get_permanent_file_identifier,
                                                        data_format=data_format)
        self.is_creating_database = False
        self.description = None
        self.missing_symbols = []
        self.fetched_data = {
            self.OHLCV: {},
            self.KLINE: {},
        }
        self.set_file_path()

    def get_permanent_file_identifier(self):
        symbols = "-".join(symbol_util.merge_symbol(symbol.symbol_str) for symbol in self.symbols)
        time_frames = "-".join(tf.value for tf in self.time_frames)
        return f"{self.exchange_name}{backtesting_constants.BACKTESTING_DATA_FILE_SEPARATOR}" \
               f"{symbols}{backtesting_constants.BACKTESTING_DATA_FILE_SEPARATOR}{time_frames}"

    async def initialize(self):
        self.create_database()
        await self.database.initialize()
        await self._check_database_content()

    def set_file_path(self) -> None:
        super().set_file_path()
        if os.path.isfile(self.file_path):
            shutil.copy(self.file_path, self.temp_file_path)

    def finalize_database(self):
        if os.path.isfile(self.file_path):
            os.remove(self.file_path)
        os.rename(self.temp_file_path, self.file_path)

    async def _check_database_content(self):
        # load description
        try:
            self.description = await data.get_database_description(self.database)
            found_exchange_name = self.description[backtesting_enums.DataFormatKeys.EXCHANGE.value]
            found_symbols = [symbol_util.parse_symbol(symbol)
                             for symbol in self.description[backtesting_enums.DataFormatKeys.SYMBOLS.value]]
            found_time_frames = self.description[backtesting_enums.DataFormatKeys.TIME_FRAMES.value]
            if found_exchange_name != self.exchange_name:
                raise backtesting_errors.IncompatibleDatafileError(f"Exchange name in database: {found_exchange_name}, "
                                                                   f"requested exchange: {self.exchange_name}")
            if found_symbols != self.symbols:
                raise backtesting_errors.IncompatibleDatafileError(f"Pairs in database: {found_symbols}, "
                                                                   f"requested exchange: {self.symbols}")
            if found_time_frames != self.time_frames:
                raise backtesting_errors.IncompatibleDatafileError(f"Time frames name in database: {found_time_frames}, "
                                                                   f"requested exchange: {self.time_frames}")
        except commons_errors.DatabaseNotFoundError:
            # newly created datafile
            self.is_creating_database = True

    async def start(self):
        self.should_stop = False
        should_stop_database = True
        self.current_step_percent = 0
        self.total_steps = len(self.time_frames) * len(self.symbols)
        try:
            self.exchange_manager = trading_api.get_exchange_manager_from_exchange_id(self.exchange_id)

            # use a secondary exchange manager to fetch candles to fix ccxt pagination issues
            # seen on ccxt 4.1.82
            other_config = copy.copy(self.config)
            other_config[commons_constants.CONFIG_TIME_FRAME] = []   # any value here to avoid crashing
            self.fetch_exchange_manager = await trading_api.create_exchange_builder(other_config, self.exchange_name) \
                .is_simulated() \
                .is_rest_only() \
                .is_exchange_only() \
                .is_future(self.exchange_manager.is_future) \
                .disable_trading_mode() \
                .use_tentacles_setup_config(self.tentacles_setup_config) \
                .build()

            await self.adapt_timestamps()

            # create/update description
            if self.is_creating_database:
                await self._create_description()
            else:
                await self._update_description()

            self.in_progress = True

            self.logger.info(f"Start collecting history on {self.exchange_name}")
            tasks = []
            for symbol_index, symbol in enumerate(self.symbols):
                if symbol in self.missing_symbols:
                    self.logger.error(f"Skipping {symbol} from backtesting data: "
                                      f"missing price history on {self.exchange_name}")
                    continue
                self.logger.info(f"Collecting history for {symbol}...")
                tasks.append(asyncio.create_task(self.get_ticker_history(self.exchange_name, symbol)))
                tasks.append(asyncio.create_task(self.get_order_book_history(self.exchange_name, symbol)))
                tasks.append(asyncio.create_task(self.get_recent_trades_history(self.exchange_name, symbol)))

                for time_frame_index, time_frame in enumerate(self.time_frames):
                    tasks.append(asyncio.create_task(self.get_ohlcv_history(self.exchange_name, symbol, time_frame)))
                    tasks.append(asyncio.create_task(self.get_kline_history(self.exchange_name, symbol, time_frame)))
                    if symbol_index == time_frame_index == 0:
                        # let tables get created
                        await asyncio.gather(*tasks)
                        tasks = []
            if tasks:
                await asyncio.gather(*tasks)

        except Exception as err:
            await self.database.stop()
            should_stop_database = False
            # Do not keep errored data file
            if os.path.isfile(self.temp_file_path):
                os.remove(self.temp_file_path)
            if not self.should_stop:
                self.logger.exception(err, True, f"Error when collecting {self.exchange_name} history for "
                                                 f"{', '.join([symbol.symbol_str for symbol in self.symbols])}: {err}")
                raise backtesting_errors.DataCollectorError(err) from err
        finally:
            await self.stop(should_stop_database=should_stop_database)

    async def stop(self, should_stop_database=True):
        self.should_stop = True
        if should_stop_database:
            await self.database.stop()
            self.finalize_database()
        await self.fetch_exchange_manager.stop()
        self.exchange_manager = None
        self.in_progress = False
        self.finished = True
        return self.finished

    async def _update_description(self):
        updated_values = {}
        if self.end_timestamp and int(self.description[backtesting_enums.DataFormatKeys.END_TIMESTAMP.value]) * 1000 < self.end_timestamp:
            updated_values["end_timestamp"] = int(self.end_timestamp/1000)
        if self.start_timestamp and int(self.description[backtesting_enums.DataFormatKeys.START_TIMESTAMP.value]) * 1000 > self.start_timestamp:
            updated_values["start_timestamp"] = int(self.start_timestamp/1000)
        if updated_values:
            updated_values["timestamp"] = time.time()
            await self.database.update(backtesting_enums.DataTables.DESCRIPTION,
                                       updated_value_by_column=updated_values,
                                       version=self.VERSION,
                                       exchange=self.exchange_name,
                                       symbols=json.dumps([symbol.symbol_str for symbol in self.symbols]),
                                       time_frames=json.dumps([tf.value for tf in self.time_frames]))

    async def get_ticker_history(self, exchange, symbol):
        pass

    async def get_order_book_history(self, exchange, symbol):
        pass

    async def get_recent_trades_history(self, exchange, symbol):
        pass

    def get_ohlcv_snapshot(self, symbol, time_frame):
        symbol_data = trading_api.get_symbol_data(self.exchange_manager, str(symbol), allow_creation=False)
        candles = trading_api.get_symbol_historical_candles(symbol_data, time_frame)
        return [
            [
                time_val,
                candles[commons_enums.PriceIndexes.IND_PRICE_OPEN.value][index],
                candles[commons_enums.PriceIndexes.IND_PRICE_HIGH.value][index],
                candles[commons_enums.PriceIndexes.IND_PRICE_LOW.value][index],
                candles[commons_enums.PriceIndexes.IND_PRICE_CLOSE.value][index],
                candles[commons_enums.PriceIndexes.IND_PRICE_VOL.value][index],
            ]
            for index, time_val in enumerate(candles[commons_enums.PriceIndexes.IND_PRICE_TIME.value])
        ]

    async def collect_historical_ohlcv(self, exchange, symbol, time_frame, time_frame_sec,
                                       start_time, end_time, progress_multiplier):
        last_progress = 0
        symbol_id = str(symbol)
        async for candles in trading_api.get_historical_ohlcv(
            self.fetch_exchange_manager, symbol_id, time_frame, start_time, end_time
        ):
            await self.save_ohlcv(
                    exchange=exchange,
                    cryptocurrency=self.exchange_manager.exchange.get_pair_cryptocurrency(symbol_id),
                    symbol=symbol.symbol_str, time_frame=time_frame, candle=candles,
                    timestamp=[candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] + time_frame_sec
                               for candle in candles],
                    multiple=True
            )
            progress = (candles[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value] - self.start_timestamp / 1000) / \
                                        ((self.end_timestamp - self.start_timestamp) / 1000) * 100
            progress_over_all_steps = progress * progress_multiplier / self.total_steps
            self.current_step_percent += progress_over_all_steps - last_progress
            self.logger.debug(f"progress: {self.current_step_percent}%")
            last_progress = progress_over_all_steps
        return last_progress

    def find_candle(self, candles, timestamp):
        for candle in candles:
            if candle[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value] == timestamp:
                return candle[-1], candle[0]
        return None, None

    async def update_ohlcv(self, exchange, symbol, time_frame, time_frame_sec,
                           database_candles, current_bot_candles):
        to_add_candles = []
        symbol_id = str(symbol)
        for up_to_date_candle in current_bot_candles:
            current_candle_time = up_to_date_candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
            equivalent_db_candle, candle_timestamp = self.find_candle(database_candles, current_candle_time)
            if equivalent_db_candle is None:
                to_add_candles.append(up_to_date_candle)
            elif equivalent_db_candle != up_to_date_candle:
                updated_value_by_column = {
                    "candle": json.dumps(up_to_date_candle)
                }
                await self.database.update(backtesting_enums.ExchangeDataTables.OHLCV,
                                           updated_value_by_column=updated_value_by_column,
                                           exchange_name=exchange,
                                           cryptocurrency=
                                           self.exchange_manager.exchange.get_pair_cryptocurrency(symbol_id),
                                           symbol=symbol.symbol_str,
                                           time_frame=time_frame.value,
                                           timestamp=str(candle_timestamp))
        if to_add_candles:
            await self.save_ohlcv(
                exchange=exchange,
                cryptocurrency=self.exchange_manager.exchange.get_pair_cryptocurrency(symbol_id),
                symbol=symbol, time_frame=time_frame, candle=to_add_candles,
                timestamp=[candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] + time_frame_sec
                           for candle in to_add_candles],
                multiple=True
            )

    async def _check_ohlcv_integrity(self, database_candles):
        # ensure no timestamp is here twice
        all_timestamps = [candle[-1][0] for candle in database_candles]
        unique_timestamps = set(all_timestamps)
        if len(unique_timestamps) != len(database_candles):
            return {
                timestamp: counter
                for timestamp, counter in collections.Counter(all_timestamps).items()
                if counter > 1
            }
        return {}

    async def get_ohlcv_history(self, exchange, symbol, time_frame):
        try:
            last_progress = 0
            time_frame_sec = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS
            # use current data from current bot
            fetch_data_id = self.get_fetch_data_id(symbol, time_frame)
            already_fetched_candles_candles = self.fetched_data[self.OHLCV][fetch_data_id]
            database_candles = []
            save_all_candles = self.is_creating_database
            updated_db = False
            if not self.is_creating_database:
                database_candles = await self._import_candles_from_datafile(exchange, symbol, time_frame)
                counters = await self._check_ohlcv_integrity(database_candles)
                if counters:
                    self.logger.warning(f"Duplicate candles in {exchange} data file for {symbol.symbol_str} "
                                        f"on {time_frame}. Problematic timestamps: {counters}. "
                                        f"Resetting database to ensure data integrity")

                    await self.delete_all(
                        backtesting_enums.ExchangeDataTables.OHLCV,
                        exchange=exchange,
                        cryptocurrency=self.exchange_manager.exchange.get_pair_cryptocurrency(str(symbol)),
                        symbol=symbol.symbol_str,
                        time_frame=time_frame
                    )
                    updated_db = True
                    save_all_candles = True
            if save_all_candles or not database_candles:
                await self.save_ohlcv(
                        exchange=exchange,
                        cryptocurrency=self.exchange_manager.exchange.get_pair_cryptocurrency(str(symbol)),
                        symbol=symbol.symbol_str, time_frame=time_frame, candle=already_fetched_candles_candles,
                        timestamp=[candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] + time_frame_sec
                                   for candle in already_fetched_candles_candles],
                        multiple=True
                )
                database_candles = await self._import_candles_from_datafile(exchange, symbol, time_frame)
                updated_db = True
            candle_times = [
                candle[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                for candle in database_candles
            ]
            # +/-1 not to fetch the last candle twice
            first_candle_data_time = min(candle_times) * 1000 - 1
            last_candle_data_time = max(candle_times) * 1000 + 1
            fill_before = self.start_timestamp and self.start_timestamp + time_frame_sec * 1000 < first_candle_data_time
            fill_after = last_candle_data_time < self.end_timestamp
            progress_per_collect = 0.5 if fill_after and fill_before else 1
            # 1. fill in any missing candle before existing candles
            if fill_before:
                # fetch missing data between required start time and actual start time in data file
                last_progress = await self.collect_historical_ohlcv(
                    exchange, symbol, time_frame, time_frame_sec, self.start_timestamp, first_candle_data_time,
                    progress_per_collect
                )
                if last_progress:
                    self.current_step_percent += 100 * progress_per_collect / self.total_steps - last_progress
                    updated_db = True
            # 2. fill in any missing candle after existing candles
            if fill_after:
                # fetch missing data between end time in data file and available data
                last_progress = await self.collect_historical_ohlcv(
                    exchange, symbol, time_frame, time_frame_sec, last_candle_data_time, self.end_timestamp,
                    progress_per_collect
                )
                if last_progress:
                    self.current_step_percent += 100 * progress_per_collect / self.total_steps - last_progress
                    updated_db = True
            if not (fill_before or fill_after):
                # nothing to collect, update progress still
                self.current_step_percent += 100 / self.total_steps
            if updated_db:
                database_candles = await self._import_candles_from_datafile(exchange, symbol, time_frame)
                counters = await self._check_ohlcv_integrity(database_candles)
                if counters:
                    self.logger.error(f"Error when checking database integrity of {exchange} "
                                      f"data file for {symbol.symbol_str}. "
                                      f"Delete this data file: {self.file_name} to reset it. "
                                      f"Problematic timestamps: {counters}")
        except Exception:
            raise

    async def _import_candles_from_datafile(self, exchange, symbol, time_frame):
        return importers.import_ohlcvs(
            await self.database.select(backtesting_enums.ExchangeDataTables.OHLCV,
                                       size=databases.SQLiteDatabase.DEFAULT_SIZE,
                                       exchange_name=exchange, symbol=symbol.symbol_str,
                                       time_frame=time_frame.value)
        )

    async def get_kline_history(self, exchange, symbol, time_frame):
        pass

    async def adapt_timestamps(self):
        lowest_timestamps = []
        for symbol in self.symbols:
            for tf in self.time_frames:
                first_timestamp = await self.get_first_candle_timestamp(
                    self.start_timestamp, symbol, tf
                )
                if first_timestamp is None:
                    self.missing_symbols.append(symbol)
                    break
                else:
                    lowest_timestamps.append(first_timestamp)
        lowest_timestamp = min(lowest_timestamps)
        # lowest_timestamp depends on self.start_timestamp if set. It will not go further
        if self.start_timestamp is None or lowest_timestamp < self.start_timestamp:
            self.start_timestamp = lowest_timestamp
        self.end_timestamp = self.end_timestamp or time.time() * 1000
        if self.start_timestamp > self.end_timestamp:
            raise backtesting_errors.DataCollectorError("start_timestamp is higher than end_timestamp")

    def get_fetch_data_id(self, symbol, timeframe):
        return f"{symbol}{timeframe.value}"

    async def get_first_candle_timestamp(self, ideal_start_timestamp, symbol, time_frame):
        try:
            symbol_data = trading_api.get_symbol_data(self.exchange_manager, str(symbol), allow_creation=False)
            candles = trading_api.get_symbol_historical_candles(symbol_data, time_frame)
            self.fetched_data[self.OHLCV][self.get_fetch_data_id(symbol, time_frame)] = self.get_ohlcv_snapshot(
                symbol, time_frame
            )
            return candles[commons_enums.PriceIndexes.IND_PRICE_TIME.value][0] * 1000
        except KeyError:
            # symbol or timeframe not available in live exchange
            fetched_candles = await self.fetch_exchange_manager.exchange.get_symbol_prices(
                str(symbol), time_frame, limit=1, since=ideal_start_timestamp
            )
            if not fetched_candles:
                return None
            self.fetched_data[self.OHLCV][self.get_fetch_data_id(symbol, time_frame)] = fetched_candles
            return fetched_candles[0][commons_enums.PriceIndexes.IND_PRICE_TIME.value] * 1000
