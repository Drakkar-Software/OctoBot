# pylint: disable=E0611
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
import asyncio
import time
import decimal

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.html_util as html_util
import octobot_commons.timestamp_util as timestamp_util

import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.exchange_data.ohlcv.channel.ohlcv as ohlcv_channel
import octobot_trading.exchanges as exchanges


class OHLCVUpdater(ohlcv_channel.OHLCVProducer):
    # set True if this channels should be notified when traded symbols are updated
    TO_NOTIFY_ON_TRADED_SYMBOLS_UPDATE: bool = True
    CHANNEL_NAME = constants.OHLCV_CHANNEL
    OHLCV_LIMIT = 5  # should be < to candle manager's MAX_CANDLES_COUNT
    OHLCV_OLD_LIMIT = constants.DEFAULT_CANDLE_HISTORY_SIZE  # should be <= to candle manager's MAX_CANDLES_COUNT
    OHLCV_ON_ERROR_TIME = 5
    OHLCV_MIN_REFRESH_TIME = 1
    OHLCV_REFRESH_TIME_THRESHOLD_BY_RETRY_ATTEMPT = [
        2,      # retry 1: t+2
        5,      # retry 2: t+7
        8 ,     # retry 3: t+15
        15,     # retry 4: t+30
        15,     # retry 5: t+45
        60      # retry N: every 60s
    ] # to prevent spamming when missing closed candles
    OHLCV_MISSING_DATA_REFRESH_RETRY_MAX_DELAY = 30 * common_constants.MINUTE_TO_SECONDS

    OHLCV_INITIALIZATION_TIMEOUT = 60
    OHLCV_INITIALIZATION_RETRY_DELAY = 10

    def __init__(self, channel):
        super().__init__(channel)
        self.tasks: dict[str, dict[common_enums.TimeFrames, asyncio.Task]] = {}
        self.is_initialized = False
        self.initialized_candles_by_tf_by_symbol = {}
        self._logged_historical_candles_incompatibility = False

    async def start(self):
        """
        Creates OHLCV refresh tasks
        """
        if self.single_update_task and not self.single_update_task.done():
            await asyncio.wait_for(self.single_update_task, self.OHLCV_INITIALIZATION_TIMEOUT)
        pairs = self._get_traded_pairs()
        if self.is_initialized:
            # is initialized: this is a resume, we need to add additional pairs
            # otherwise, this is a first start, additional pairs will be added via modify()
            pairs += self._get_additional_traded_pairs()
        if not self.is_initialized:
            await self._initialize(pairs, False)
        if self.channel is not None:
            if self.channel.is_paused:
                await self.pause()
            else:
                self.tasks = {
                    pair: {
                        time_frame: asyncio.create_task(self._candle_update_loop(time_frame, pair))
                        for time_frame in self._get_time_frames(pair)
                        if self._should_maintain_candle(time_frame, pair)
                    }
                    for pair in pairs
                }

    def _get_traded_pairs(self) -> list[str]:
        return self.channel.exchange_manager.exchange_config.traded_symbol_pairs
    
    def _get_additional_traded_pairs(self) -> list[str]:
        return self.channel.exchange_manager.exchange_config.additional_traded_pairs

    def _get_time_frames(self, pair: str) -> list[common_enums.TimeFrames]:
        configured_time_frames = self.channel.exchange_manager.exchange_config.available_time_frames
        if pair in self._get_additional_traded_pairs():
            # this is an additional pair, we need to use additional time frames as well if any
            return configured_time_frames + self.channel.exchange_manager.exchange_config.additional_time_frames
        return configured_time_frames

    async def modify(self, added_pairs=None, removed_pairs=None):
        if added_pairs:
            # initialize pairs history if needed
            await self._initialize(added_pairs, False)
            # for each pair, create a new update task if needed
            for pair in added_pairs:
                if pair not in self.tasks:
                    self.tasks[pair] = {}
                for time_frame in self._get_time_frames(pair):
                    if (
                        (time_frame not in self.tasks[pair] or self.tasks[pair][time_frame].done())
                        and self._should_maintain_candle(time_frame, pair)
                    ):
                        self.tasks[pair][time_frame] = asyncio.create_task(self._candle_update_loop(time_frame, pair))
        if removed_pairs:
            for pair in removed_pairs:
                if pair in self.tasks:
                    for time_frame in self.tasks[pair]:
                        if not self.tasks[pair][time_frame].done():
                            self.tasks[pair][time_frame].cancel()
                        del self.tasks[pair][time_frame]
                    del self.tasks[pair]

    def _should_maintain_candle(self, time_frame, pair):
        return not (
            exchanges.is_channel_managed_by_websocket(self.channel.exchange_manager, self.CHANNEL_NAME)
            and self.channel.exchange_manager.exchange_web_socket.is_time_frame_supported(time_frame)
        )

    async def fetch_and_push(self):
        return await self._initialize(
            self._get_traded_pairs() + self._get_additional_traded_pairs(),
            True
        )

    async def _initialize(self, pairs: list[str], push_initialization_candles: bool):
        try:
            initial_candles_data = await asyncio.gather(*[
                self._initialize_candles(time_frame, pair, True)
                for pair in pairs
                for time_frame in self._get_time_frames(pair)
            ])
            if push_initialization_candles:
                await self._push_initial_candles(initial_candles_data)
        except Exception as e:
            self.logger.exception(e, True, f"Error while initializing candles: {e}")
        finally:
            self.logger.debug(f"Candle history initial fetch completed for {pairs}")
            self.is_initialized = True

    def _get_historical_candles_count(self):
        if self.channel.exchange_manager.exchange_config.required_historical_candles_count > 0:
            if self.channel.exchange_manager.exchange_name in constants.FULL_CANDLE_HISTORY_EXCHANGES:
                return self.channel.exchange_manager.exchange_config.required_historical_candles_count
            if not self._logged_historical_candles_incompatibility:
                self.logger.warning(f"Can't initialize the required "
                                    f"{self.channel.exchange_manager.exchange_config.required_historical_candles_count}"
                                    f" historical candles: {self.channel.exchange_manager.exchange_name} is not "
                                    f"supporting large candles history. Using the {self.OHLCV_OLD_LIMIT} "
                                    f"latest candles instead.")
                self._logged_historical_candles_incompatibility = True
        return self.OHLCV_OLD_LIMIT

    async def _get_init_candles(self, time_frame, pair):
        historical_candles_count_limit = self._get_historical_candles_count()
        if historical_candles_count_limit > constants.DEFAULT_CANDLE_HISTORY_SIZE:
            tf_seconds = common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
            end_time = time.time() * common_constants.MSECONDS_TO_SECONDS
            # add 1 to historical_candles_count_limit to fetch the required count (otherwise one is missing)
            start_time = end_time - (historical_candles_count_limit + 1) * tf_seconds * \
                common_constants.MSECONDS_TO_SECONDS
            candles = []
            async for new_candles in exchanges.get_historical_ohlcv(self.channel.exchange_manager, pair,
                                                                    time_frame, start_time, end_time):
                candles += new_candles
            return candles
        candles: list = await self.channel.exchange_manager.exchange \
            .get_symbol_prices(pair, time_frame, limit=self.OHLCV_OLD_LIMIT)
        return candles

    async def _initialize_candles(
        self, time_frame: common_enums.TimeFrames, pair: str, should_retry: bool
    ) -> (str, common_enums.TimeFrames, list):
        """
        Manage timeframe OHLCV data refreshing for all pairs
        :return: a tuple with (trading pair, time_frame, fetched candles)
        """
        self._set_initialized(pair, time_frame, False)
        # fetch history
        candles = None
        if self.channel.exchange_manager.exchange_config is None:
            # exchange stopped
            return None
        try:
            candles: list = await self._get_init_candles(time_frame, pair)
        except errors.FailedRequest as e:
            self.logger.warning(str(e))
        if self.channel.exchange_manager.exchange_symbols_data is None:
            # exchange stopped
            return None
        if candles and len(candles) > 1:
            self._set_initialized(pair, time_frame, True)
            await self.channel.exchange_manager.get_symbol_data(pair) \
                .handle_candles_update(time_frame, candles[:-1], replace_all=True, partial=False, upsert=False)
            self.logger.debug(f"Candle history loaded for {pair} on {time_frame}")
            self._set_mark_price_from_candle(pair, candles[-1])
            return pair, time_frame, candles
        elif should_retry:
            # When candle history cannot be loaded, retry to load it later
            self.logger.warning(f"Failed to initialize candle history for {pair} on {time_frame}. Retrying in "
                                f"{self.OHLCV_INITIALIZATION_RETRY_DELAY} seconds")
            # retry only once
            await asyncio.sleep(self.OHLCV_INITIALIZATION_RETRY_DELAY)
            return await self._initialize_candles(time_frame, pair, False)
        else:
            self.logger.warning(f"Failed to initialize candle history for {pair} on {time_frame}. Retrying on "
                                f"the next time frame update")
            return None

    def _set_mark_price_from_candle(self, pair, candle):
        # Initialize mark price with last candle close to allow trading low liquidity markets. Those that might
        # take some time to produce a trade and therefore initialize their mark price, which is
        # required to create orders and might block the trading initialization
        price = decimal.Decimal(str(candle[common_enums.PriceIndexes.IND_PRICE_CLOSE.value]))
        self.channel.exchange_manager.get_symbol_data(pair).handle_mark_price_update(
            price,
            enums.MarkPriceSources.TICKER_CLOSE_PRICE.value
        )
        if self.channel.exchange_manager.exchange_personal_data.portfolio_manager is None:
            if self.channel.exchange_manager.is_trading:
                self.logger.error(
                    f"Trading exchange manager without portfolio_manager "
                    f"on {self.channel.exchange_manager.exchange_name}"
                )
        else:
            self.channel.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
                value_converter.update_last_price(pair, price)

    async def _push_initial_candles(self, initial_candles_data):
        self.logger.debug("Pushing completed initialization candles")
        for initial_candles_tuple in initial_candles_data:
            if initial_candles_tuple is not None:
                pair, time_frame, candles = initial_candles_tuple
                await self._push_complete_candles(time_frame, pair, candles)

    async def _push_complete_candles(self, time_frame, pair, candles):
        await self.push(time_frame, pair, candles[:-1], partial=True)  # push only completed candles

    async def _ensure_candles_initialization(self, pair):
        init_coroutines = tuple(
            self._initialize_candles(time_frame, pair, False)
            for time_frame, initialized in self.initialized_candles_by_tf_by_symbol[pair].items()
            if not initialized
        )
        # call gather only if init_coroutines is not empty for optimization purposes
        if init_coroutines:
            await asyncio.gather(*init_coroutines)

    async def _candle_update_loop(self, time_frame, pair):
        self.logger.debug(f"Starting ohlcv updater loop for {pair} on {time_frame}")
        time_frame_seconds: int = common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
        time_frame_sleep: int = time_frame_seconds
        last_candle_timestamp: float = 0

        current_candle_start_time = 0
        attempt = 1
        while not self.should_stop and not self.channel.is_paused:
            start_update_time = time.time()
            iteration_candle_start_time = start_update_time - (start_update_time % time_frame_seconds)
            try:
                if iteration_candle_start_time == current_candle_start_time:
                    attempt += 1
                else:
                    current_candle_start_time = iteration_candle_start_time
                    attempt = 1
                await self._ensure_candles_initialization(pair)
                # skip uninitialized candles
                if self.initialized_candles_by_tf_by_symbol[pair][time_frame]:
                    candles: list = await self.channel.exchange_manager.exchange.get_symbol_prices(
                        pair,
                        time_frame,
                        limit=self.OHLCV_LIMIT)
                    if candles:
                        last_candle: list = candles[-1]
                    else:
                        last_candle: list = []

                    if last_candle and len(candles) > 1:
                        last_candle_timestamp, sleep_time = await self._refresh_current_candle(
                            time_frame, pair, candles, last_candle, last_candle_timestamp,
                            iteration_candle_start_time, time_frame_seconds, attempt
                        )
                        updated_sleep_time = self._ensure_correct_sleep_time(
                            sleep_time, iteration_candle_start_time, time_frame_seconds
                        )
                        await asyncio.sleep(updated_sleep_time)
                    else:
                        # not enough candles: retry soon
                        sleep_time = self._ensure_correct_sleep_time(
                            self._get_missing_candle_retry_sleep_time(attempt),
                            iteration_candle_start_time, time_frame_seconds
                        )
                        self.logger.debug(f"Missing candles in request results for {pair} on {time_frame}, refreshing "
                                          f"in {sleep_time} seconds (available candles: {candles}).")
                        await asyncio.sleep(sleep_time)
                else:
                    # candles on this time frame have not been initialized: sleep until the next candle update
                    await asyncio.sleep(max(0.0, time_frame_sleep - (time.time() - start_update_time)))
            except errors.FailedRequest as err:
                # avoid spamming on disconnected situation
                sleep_time = self._ensure_correct_sleep_time(
                    self._get_missing_candle_retry_sleep_time(attempt),
                    iteration_candle_start_time, time_frame_seconds
                )
                sleep_time = max(sleep_time, constants.DEFAULT_FAILED_REQUEST_RETRY_TIME)
                self.logger.warning(
                    f"Impossible to fetch {time_frame.value} {pair} candles. Retry in {sleep_time} seconds: "
                    f"{html_util.get_html_summary_if_relevant(err)}"
                )
                await asyncio.sleep(sleep_time)
            except errors.UnSupportedSymbolError as err:
                self.logger.warning(
                    f"{self.channel.exchange_manager.exchange_name} is not supporting {pair} on {time_frame.value}: {err}")
                if await self._remove_unsupported_pairs(pair):                    
                    # Exit the loop after removing the pair to avoid endless retries
                    return
            except errors.NotSupported as err:
                self.logger.warning(
                    f"{self.channel.exchange_manager.exchange_name} is not supporting updates: {err}")
                await self.pause()
            except Exception as e:
                self.logger.exception(
                    e,
                    True,
                    f"Failed to update ohlcv data for {pair} on {time_frame} : "
                    f"{html_util.get_html_summary_if_relevant(e)}"
                )
                await asyncio.sleep(self.OHLCV_ON_ERROR_TIME)

    async def _refresh_current_candle(
        self, time_frame, pair, candles, last_candle, last_candle_timestamp,
        iteration_candle_start_time, time_frame_seconds, attempt
    ):
        current_candle_timestamp: float = last_candle[common_enums.PriceIndexes.IND_PRICE_TIME.value]
        should_sleep_time: float = current_candle_timestamp + time_frame_seconds - time.time()

        # if we're trying to refresh the current candle => useless
        if last_candle_timestamp == current_candle_timestamp:
            if should_sleep_time < 0:
                # up-to-date candle is not yet available on exchange: retry in a few seconds
                should_sleep_time = self._ensure_correct_sleep_time(
                    self._get_missing_candle_retry_sleep_time(attempt),
                    iteration_candle_start_time,
                    time_frame_seconds
                )
            else:
                should_sleep_time = self._ensure_correct_sleep_time(
                    should_sleep_time + time_frame_seconds + self._get_missing_candle_retry_sleep_time(attempt),
                    iteration_candle_start_time,
                    time_frame_seconds
                )
            self.logger.debug(
                f"Failed to fetch up-to-date candle for {pair} on {time_frame.value}: "
                f"latest candle open time: {last_candle_timestamp} ({timestamp_util.convert_timestamp_to_datetime(last_candle_timestamp)}). "
                f"Retrying in {round(should_sleep_time, 2)} seconds."
            )

        else:
            # A fresh candle happened
            last_candle_timestamp = current_candle_timestamp
            await self._push_complete_candles(time_frame, pair, candles)
        return last_candle_timestamp, should_sleep_time

    def _get_missing_candle_retry_sleep_time(self, attempt):
        if attempt < len(self.OHLCV_REFRESH_TIME_THRESHOLD_BY_RETRY_ATTEMPT):
            return self.OHLCV_REFRESH_TIME_THRESHOLD_BY_RETRY_ATTEMPT[attempt - 1]
        return self.OHLCV_REFRESH_TIME_THRESHOLD_BY_RETRY_ATTEMPT[-1]

    def _ensure_correct_sleep_time(self, sleep_time_candidate, iteration_candle_start_time, time_frame_seconds):
        if sleep_time_candidate < OHLCVUpdater.OHLCV_MIN_REFRESH_TIME:
            return OHLCVUpdater.OHLCV_MIN_REFRESH_TIME
        else:
            max_sleep_time = max(iteration_candle_start_time + time_frame_seconds - time.time(), 0)
            # ensure does not sleep more than missing time before next candle
            return min(sleep_time_candidate, max_sleep_time)

    def _set_initialized(self, pair, time_frame, initialized):
        if pair not in self.initialized_candles_by_tf_by_symbol:
            self.initialized_candles_by_tf_by_symbol[pair] = {}
        self.initialized_candles_by_tf_by_symbol[pair][time_frame] = initialized

    async def _remove_unsupported_pairs(self, pair: str) -> bool:
        # For now only remove the pair from the traded pairs if it's an option exchange
        if self.channel.exchange_manager.is_option:
            self.logger.warning(f"Removing {pair} from traded pairs...")
            await self.channel.exchange_manager.exchange_config.remove_traded_symbols([pair])
            return True
        return False

    async def resume(self) -> None:
        await super().resume()
        if not self.is_running:
            for tasks in self.tasks.values():
                for task in tasks.values():
                    task.cancel()
            await self.run()

    async def stop(self) -> None:
        await super().stop()
        if self.tasks:
            for tasks in self.tasks.values():
                for task in tasks.values():
                    task.cancel()
            self.tasks = {}
