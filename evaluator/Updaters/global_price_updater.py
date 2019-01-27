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
import time
import copy
from concurrent.futures import CancelledError

from tools.logging.logging_util import get_logger
from backtesting.backtesting import Backtesting, BacktestingEndedException
from config import TimeFramesMinutes, MINUTE_TO_SECONDS, UPDATER_MAX_SLEEPING_TIME
from tools.time_frame_manager import TimeFrameManager


class GlobalPriceUpdater:

    def __init__(self, exchange):
        self.logger = get_logger(self.__class__.__name__)
        self.exchange = exchange
        self.keep_running = True
        self.evaluator_task_manager_by_time_frame_by_symbol = {}
        self.refreshed_times = {}
        self.time_frame_last_update = {}
        self.symbols = None
        self.symbol_evaluators = []
        self.watcher = None
        self.in_backtesting = False

    # add a time frame to watch and its related evaluator task manager
    def register_evaluator_task_manager(self, time_frame, evaluator_task_manager):
        if time_frame not in self.evaluator_task_manager_by_time_frame_by_symbol:
            self.evaluator_task_manager_by_time_frame_by_symbol[time_frame] = {}

        # one evaluator_task_manager per time frame per symbol
        symbol = evaluator_task_manager.get_symbol()
        self.evaluator_task_manager_by_time_frame_by_symbol[time_frame][symbol] = evaluator_task_manager

        if self.symbols is None:
            self.symbols = []
        if symbol not in self.symbols:
            self.symbols.append(symbol)

        symbol_evaluator = evaluator_task_manager.get_symbol_evaluator()
        if symbol_evaluator not in self.symbol_evaluators:
            self.symbol_evaluators.append(symbol_evaluator)

    async def start_update_loop(self):

        error = None
        try:
            time_frames = self.evaluator_task_manager_by_time_frame_by_symbol.keys()

            # sort time frames to update them in order of accuracy
            time_frames = TimeFrameManager.sort_time_frames(time_frames)

            if time_frames and self.symbols:

                self.in_backtesting = self._init_backtesting_if_necessary(time_frames)

                # init refreshed_times at 0 for each time frame
                self.refreshed_times = {key: {symbol: 0 for symbol in self.symbols} for key in time_frames}

                # init last refresh times at 0 for each time frame
                self.time_frame_last_update = {key: {symbol: 0 for symbol in self.symbols} for key in time_frames}

                while self.keep_running:
                    try:
                        await self._trigger_update(time_frames)
                    except CancelledError:
                        self.logger.info("Update tasks cancelled.")
                    except Exception as e:
                        self.logger.error(f"exception when triggering update: {e}")
                        self.logger.exception(e)
            else:
                self.logger.warning("no time frames to monitor, going to sleep.")

        except Exception as e:
            self.logger.exception(e)
            if self.watcher is not None:
                error = e

        finally:
            if self.in_backtesting \
                    and self.symbols is not None \
                    and not self.exchange.get_exchange().get_backtesting().get_is_finished(self.symbols):
                if error is None:
                    error = "backtesting did not finish properly."
                if self.watcher is not None:
                    self.watcher.set_error(error)
                self.logger.error(error)

    async def _trigger_update(self, time_frames):
        now = time.time()

        update_tasks = []

        for time_frame in time_frames:
            for symbol in self.symbols:
                # backtesting doesn't need to wait a specific time frame to end to refresh data
                if self.in_backtesting:
                    update_tasks.append(self._refresh_backtesting_time_frame_data(time_frame, symbol))

                # if data from this time frame needs an update
                elif now - self.time_frame_last_update[time_frame][symbol] \
                        >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                    update_tasks.append(self._refresh_time_frame_data(time_frame, symbol))

        await asyncio.gather(*update_tasks)

        if update_tasks:
            await self.trigger_symbols_finalize()

        if self.in_backtesting:
            await self.update_backtesting_order_status()

        if self.keep_running:
            await self._update_pause(now)

    async def trigger_symbols_finalize(self):
        sort_symbol_evaluators = sorted(self.symbol_evaluators,
                                        key=lambda s: abs(s.get_average_strategy_eval(self.exchange)),
                                        reverse=True)
        for symbol_evaluator in sort_symbol_evaluators:
            await symbol_evaluator.finalize(self.exchange)

    async def force_refresh_data(self, time_frame, symbol):
        if not self.in_backtesting:
            await self._refresh_time_frame_data(time_frame, symbol, notify=False)

    # calculate task sleep time between each refresh
    async def _update_pause(self, now):
        sleeping_time = 0
        if not self.in_backtesting:
            sleeping_time = UPDATER_MAX_SLEEPING_TIME - (time.time() - now)
        if sleeping_time > 0:
            await asyncio.sleep(sleeping_time)

    async def _refresh_backtesting_time_frame_data(self, time_frame, symbol):
        try:
            if self.exchange.get_exchange().should_update_data(time_frame, symbol):
                await self._refresh_data(time_frame, symbol)
        except BacktestingEndedException as e:
            self.logger.info(e)
            self.keep_running = False
            await self.exchange.get_exchange().end_backtesting(symbol)

    # currently used only during backtesting, will force refresh of each supervised task
    async def update_backtesting_order_status(self):
        order_manager = self.exchange.get_exchange_manager().get_trader().get_order_manager()
        await order_manager.force_update_order_status(simulated_time=True)

    async def _refresh_time_frame_data(self, time_frame, symbol, notify=True):
        try:
            await self._refresh_data(time_frame, symbol, notify=notify)
            self.time_frame_last_update[time_frame][symbol] = time.time()
        except CancelledError as e:
            raise e
        except Exception as e:
            self.logger.error(f" when refreshing data for time frame {time_frame}: {e}")
            self.logger.exception(e)

    # notify the time frame's evaluator task manager to refresh its data
    async def _refresh_data(self, time_frame, symbol, limit=None, notify=True):
        evaluator_task_manager_to_notify = self.evaluator_task_manager_by_time_frame_by_symbol[time_frame][symbol]

        numpy_candle_data = copy.deepcopy(await evaluator_task_manager_to_notify.exchange.get_symbol_prices(
            evaluator_task_manager_to_notify.symbol,
            evaluator_task_manager_to_notify.time_frame,
            limit=limit,
            return_list=False))

        evaluator_task_manager_to_notify.evaluator.set_data(numpy_candle_data)
        self.refreshed_times[time_frame][symbol] += 1
        if notify:
            await evaluator_task_manager_to_notify.notify(self.__class__.__name__)

    def _init_backtesting_if_necessary(self, time_frames):

        # figure out from an evaluator if back testing is running for this symbol
        evaluator_task_manager = \
            self.evaluator_task_manager_by_time_frame_by_symbol[time_frames[0]][self.symbols[0]]

        # test if we need to initialize backtesting features
        backtesting_enabled = Backtesting.enabled(evaluator_task_manager.get_evaluator().get_config())
        if backtesting_enabled:
            for symbol in self.symbols:
                self.exchange.get_exchange().init_candles_offset(time_frames, symbol)

        return backtesting_enabled

    def stop(self):
        self.keep_running = False

    def get_refreshed_times(self, time_frame, symbol):
        return self.refreshed_times[time_frame][symbol]

    def set_watcher(self, watcher):
        self.watcher = watcher
