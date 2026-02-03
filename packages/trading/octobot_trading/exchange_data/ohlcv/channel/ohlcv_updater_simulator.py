#  Drakkar-Software OctoBot-Trading
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
import octobot_backtesting.api as api

import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors

import octobot_trading.exchange_data.ohlcv.channel.ohlcv_updater as ohlcv_updater
import octobot_trading.util as util


class OHLCVUpdaterSimulator(ohlcv_updater.OHLCVUpdater):
    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer
        self.exchange_name = self.channel.exchange_manager.exchange_name

        self.initial_timestamp = api.get_backtesting_current_time(self.channel.exchange_manager.exchange.backtesting)
        self.last_timestamp_pushed = 0
        self.time_consumer = None

        self.future_candle_time_frame = self.channel.exchange_manager.exchange_config.get_shortest_time_frame()
        self.future_candle_sec_length = enums.TimeFramesMinutes[self.future_candle_time_frame] * \
                                        constants.MINUTE_TO_SECONDS

        self.last_candles_by_pair_by_time_frame = {}
        self.require_last_init_candles_pairs_push = False
        self.traded_pairs = self._get_traded_pairs()
        self.traded_time_frame = self._get_time_frames()

    async def start(self):
        if not self.is_initialized:
            await self._initialize(self.traded_pairs, False)
        await self.resume()

    async def handle_timestamp(self, timestamp, **kwargs):
        try:
            pushed_data = False
            for pair in self.traded_pairs:
                for time_frame in self.traded_time_frame:
                    # Use last_timestamp_pushed + 1 for inferior timestamp to avoid select of an already selected candle
                    # (selection is <= and >=)
                    # Use timestamp + self.future_candle_sec_length to include the future candle on the future candles
                    # time frame that will be sorted in exchange simulator for later uses.
                    ohlcv_data: list = await self.exchange_data_importer.get_ohlcv_from_timestamps(
                        exchange_name=self.exchange_name,
                        symbol=pair,
                        time_frame=time_frame,
                        inferior_timestamp=self.last_timestamp_pushed + 1,
                        superior_timestamp=timestamp + (self.future_candle_sec_length
                                                        if self.future_candle_time_frame is time_frame else 0)
                    )
                    if ohlcv_data:
                        pushed_data = await self._handle_ohlcv_data(ohlcv_data, time_frame, pair, timestamp)
                    elif self.require_last_init_candles_pairs_push:
                        # triggered on first iteration to initialize large candles that might be pushed much later
                        # otherwise but are required to complete TA evaluation
                        if time_frame.value in self.last_candles_by_pair_by_time_frame[pair]:
                            await self.push(time_frame,
                                            pair,
                                            [self.last_candles_by_pair_by_time_frame[pair][time_frame.value][-1]],
                                            partial=True)
                            pushed_data = True
            if (
                not self.channel.exchange_manager.exchange.is_skipping_empty_candles_in_ohlcv_fetch()
                and not pushed_data
            ):
                self.channel.exchange_manager.exchange.is_unreachable = True

        except errors.DatabaseNotFoundError as e:
            self.logger.warning(f"Not enough data : {e}")
            await self.pause()
            await self.stop()
        except IndexError as e:
            self.logger.warning(f"Failed to access ohlcv_data : {e}")
        except Exception as e:
            self.logger.exception(e, True, f"Error when updating from timestamp: {e}")
        finally:
            self.last_timestamp_pushed = timestamp
            self.require_last_init_candles_pairs_push = False

    async def _handle_ohlcv_data(self, ohlcv_data, time_frame, pair, timestamp):
        has_future_candle = False
        if self.future_candle_time_frame is time_frame:
            if ohlcv_data[-1][-1][enums.PriceIndexes.IND_PRICE_TIME.value] == timestamp:
                # register future candle
                self.channel.exchange_manager.exchange.get_current_future_candles()[pair][time_frame.value] = \
                    ohlcv_data[-1][-1]
                # do not push future candle
                has_future_candle = True
            else:
                # if no future candle available
                # (end of backtesting of missing data: reset future candle)
                self.channel.exchange_manager.exchange.get_current_future_candles()[pair][time_frame.value] = None

            # There should always be at least 2 candles in read data, otherwise this means that
            # the exchange was down for some time. Consider it unreachable
            if (
                len(ohlcv_data) < 2 and
                not self.channel.exchange_manager.exchange.is_skipping_empty_candles_in_ohlcv_fetch()
            ):
                self.channel.exchange_manager.exchange.is_unreachable = True
        if not has_future_candle or len(ohlcv_data) > 1:
            # push current candle(s)
            candles = ohlcv_data[:-1] if has_future_candle else ohlcv_data
            await self.push(time_frame,
                            pair,
                            [ohlcv[-1] for ohlcv in candles],
                            partial=True)
            return True
        return False

    async def pause(self):
        await util.pause_time_consumer(self)

    async def stop(self):
        await util.stop_and_pause(self)

    async def resume(self):
        await util.resume_time_consumer(self, self.handle_timestamp)

    def _get_traded_pairs(self):
        return api.get_available_symbols(self.exchange_data_importer)

    def _get_time_frames(self, *_):
        return self.channel.exchange_manager.exchange.get_time_frames(self.exchange_data_importer)

    async def _initialize_candles(self, time_frame, pair, should_retry):
        # fetch history
        ohlcv_data = None
        try:
            # only load candles starting from the star time of the backtesting
            ohlcv_data: list = await self.exchange_data_importer.get_ohlcv_from_timestamps(
                exchange_name=self.exchange_name,
                symbol=pair,
                time_frame=time_frame,
                limit=self.OHLCV_OLD_LIMIT,
                inferior_timestamp=self.initial_timestamp,
                superior_timestamp=self.initial_timestamp)
            candles_len = len(ohlcv_data)
            self.logger.info(f"Loaded pre-backtesting starting timestamp historical "
                             f"candles for: {pair} in {time_frame}: {candles_len} "
                             f"candle{'s' if candles_len > 1 else ''}")
        except Exception as e:
            self.logger.exception(e, True, f"Error while fetching historical candles: {e}")
        if pair not in self.last_candles_by_pair_by_time_frame:
            self.last_candles_by_pair_by_time_frame[pair] = {}
        if ohlcv_data:
            # init historical candles
            await self.channel.exchange_manager.get_symbol_data(pair) \
                .handle_candles_update(time_frame,
                                       [ohlcv[-1] for ohlcv in ohlcv_data],
                                       replace_all=True,
                                       partial=False,
                                       upsert=False)
            self.last_candles_by_pair_by_time_frame[pair][time_frame.value] = ohlcv_data[-1]
            self.require_last_init_candles_pairs_push = True
        # self.initial_timestamp - 1 to re-select this candle and push it when init step will be over
        self.last_timestamp_pushed = self.initial_timestamp - 1
