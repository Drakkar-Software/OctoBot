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
import logging
import os
import time

import octobot_backtesting.collectors as collector
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.errors as errors
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.time_frame_manager as time_frame_manager
import tentacles.Backtesting.importers.exchanges.generic_exchange_importer as generic_exchange_importer

try:
    import octobot_trading.api as trading_api
    import octobot_trading.enums as trading_enums
    import octobot_trading.errors as trading_errors
except ImportError:
    logging.error("ExchangeHistoryDataCollector requires OctoBot-Trading package installed")


class ExchangeHistoryDataCollector(collector.AbstractExchangeHistoryCollector):
    IMPORTER = generic_exchange_importer.GenericExchangeDataImporter

    def __init__(self, config, exchange_name, exchange_type, tentacles_setup_config, symbols, time_frames,
                 use_all_available_timeframes=False,
                 data_format=backtesting_enums.DataFormats.REGULAR_COLLECTOR_DATA,
                 start_timestamp=None,
                 end_timestamp=None):
        super().__init__(config, exchange_name, exchange_type, tentacles_setup_config, symbols, time_frames,
                         use_all_available_timeframes, data_format=data_format,
                         start_timestamp=start_timestamp, end_timestamp=end_timestamp)
        self.exchange = None
        self.exchange_manager = None

    async def start(self):
        self.should_stop = False
        should_stop_database = True
        try:
            use_future = self.exchange_type == trading_enums.ExchangeTypes.FUTURE
            self.exchange_manager = await trading_api.create_exchange_builder(self.config, self.exchange_name) \
                .is_simulated() \
                .is_rest_only() \
                .is_exchange_only() \
                .is_future(use_future) \
                .disable_trading_mode() \
                .use_tentacles_setup_config(self.tentacles_setup_config) \
                .build()

            self.exchange = self.exchange_manager.exchange
            self._load_timeframes_if_necessary()

            await self.check_timestamps()

            # create description
            await self._create_description()

            self.total_steps = len(self.time_frames) * len(self.symbols)
            self.in_progress = True

            self.logger.info(f"Start collecting history on {self.exchange_name}")
            for symbol_index, symbol in enumerate(self.symbols):
                self.logger.info(f"Collecting history for {symbol}...")
                await self.get_ticker_history(self.exchange_name, symbol)
                await self.get_order_book_history(self.exchange_name, symbol)
                await self.get_recent_trades_history(self.exchange_name, symbol)

                for time_frame_index, time_frame in enumerate(self.time_frames):
                    self.current_step_index = (symbol_index * len(self.time_frames)) + time_frame_index + 1
                    self.logger.info(
                        f"[{time_frame_index}/{len(self.time_frames)}] Collecting {symbol} history on {time_frame}...")
                    await self.get_ohlcv_history(self.exchange_name, symbol, time_frame)
                    await self.get_kline_history(self.exchange_name, symbol, time_frame)
        except Exception as err:
            await self.database.stop()
            should_stop_database = False
            # Do not keep errored data file
            if os.path.isfile(self.temp_file_path):
                os.remove(self.temp_file_path)
            if not self.should_stop:
                self.logger.exception(err, True, f"Error when collecting {self.exchange_name} history for "
                                                 f"{', '.join([str(symbol) for symbol in self.symbols])}: {err}")
                raise errors.DataCollectorError(err)
        finally:
            await self.stop(should_stop_database=should_stop_database)

    def _load_all_available_timeframes(self):
        allowed_timeframes = set(tf.value for tf in commons_enums.TimeFrames)
        self.time_frames = [commons_enums.TimeFrames(time_frame)
                            for time_frame in self.exchange_manager.client_time_frames
                            if time_frame in allowed_timeframes]

    async def stop(self, should_stop_database=True):
        self.should_stop = True
        if self.exchange_manager is not None:
            await self.exchange_manager.stop()
        if should_stop_database:
            await self.database.stop()
            self.finalize_database()
        self.exchange_manager = None
        self.in_progress = False
        self.finished = True
        return self.finished

    async def get_ticker_history(self, exchange, symbol):
        pass

    async def get_order_book_history(self, exchange, symbol):
        pass

    async def get_recent_trades_history(self, exchange, symbol):
        pass

    async def get_ohlcv_history(self, exchange, symbol, time_frame):
        self.current_step_percent = 0
        # use time_frame_sec to add time to save the candle closing time
        time_frame_sec = commons_enums.TimeFramesMinutes[time_frame] * commons_constants.MINUTE_TO_SECONDS
        symbol_id = str(symbol)
        cryptocurrency = self.exchange_manager.exchange.get_pair_cryptocurrency(symbol_id)
        if self.start_timestamp is not None:
            start_time = self.start_timestamp
            end_time = self.end_timestamp or time.time() * 1000
            first_candle_timestamp = await self.get_first_candle_timestamp(
                self.start_timestamp, symbol, time_frame
            ) * 1000
            if self.start_timestamp < first_candle_timestamp:
                start_time = first_candle_timestamp
            async for hist_candles in trading_api.get_historical_ohlcv(self.exchange_manager, symbol_id, time_frame,
                                                                       start_time, end_time):
                if hist_candles:
                    self.current_step_percent = \
                        (hist_candles[-1][commons_enums.PriceIndexes.IND_PRICE_TIME.value] - start_time / 1000) / \
                        ((end_time - start_time) / 1000) * 100
                    self.logger.info(f"[{self.current_step_percent}%] historical data fetched for {symbol} {time_frame}")
                    await self.save_ohlcv(
                        exchange=exchange,
                        cryptocurrency=cryptocurrency,
                        symbol=symbol.symbol_str, time_frame=time_frame, candle=hist_candles,
                        timestamp=[candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] + time_frame_sec
                                   for candle in hist_candles],
                        multiple=True)
        else:
            try:
                candles = await self.exchange.get_symbol_prices(symbol_id, time_frame)
                if candles:
                    await self.save_ohlcv(exchange=exchange,
                                          cryptocurrency=cryptocurrency,
                                          symbol=symbol.symbol_str, time_frame=time_frame, candle=candles,
                                          timestamp=[candle[0] + time_frame_sec for candle in candles], multiple=True)
                else:
                    self.logger.error(f"No candles for {symbol} on {time_frame} ({exchange})")
            except trading_errors.FailedRequest as err:
                self.logger.exception(err, False)
                self.logger.warning(f"Ignored {symbol} {time_frame} candles on {exchange} ({err})")

    async def get_kline_history(self, exchange, symbol, time_frame):
        pass

    async def check_timestamps(self):
        if self.start_timestamp is not None:
            lowest_timestamp = min([
                await self.get_first_candle_timestamp(
                    self.start_timestamp, symbol, time_frame_manager.find_min_time_frame(self.time_frames)
                )
                for symbol in self.symbols
            ])
            if lowest_timestamp > self.start_timestamp:
                self.start_timestamp = lowest_timestamp
            if self.start_timestamp > (self.end_timestamp if self.end_timestamp else (time.time() * 1000)):
                raise errors.DataCollectorError("start_timestamp is higher than end_timestamp")

    async def get_first_candle_timestamp(self, ideal_start_timestamp, symbol, time_frame):
        try:
            return (
                await self.exchange.get_symbol_prices(str(symbol), time_frame, limit=1, since=ideal_start_timestamp)
            )[0][commons_enums.PriceIndexes.IND_PRICE_TIME.value]
        except (trading_errors.FailedRequest, IndexError) as err:
            raise errors.DataCollectorError(
                f"Impossible to initialize {self.exchange_name} data collector: {err}. This means that {symbol} "
                f"for the {time_frame.value} time frame is not supported in this context on {self.exchange_name}."
            )
