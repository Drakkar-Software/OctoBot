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

import threading
import time
from tools.logging.logging_util import get_logger
import copy

from backtesting.backtesting import Backtesting, BacktestingEndedException
from config import TimeFramesMinutes, MINUTE_TO_SECONDS, UPDATER_MAX_SLEEPING_TIME
from tools.time_frame_manager import TimeFrameManager

"""
This class (Thread) supervise evaluators data refresh :
- Get updated data from exchange
- Deliver new data in each evaluator that needs to be updated (specified by its time frame) 
"""


class SymbolTimeFramesDataUpdaterThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.evaluator_threads_manager_by_time_frame = {}
        self.refreshed_times = {}
        self.time_frame_last_update = {}
        self.keep_running = True
        self.logger = get_logger(self.__class__.__name__)
        self.watcher = None

    # add a time frame to watch and its related evaluator task manager
    def register_evaluator_thread_manager(self, time_frame, evaluator_thread_manager):
        self.evaluator_threads_manager_by_time_frame[time_frame] = evaluator_thread_manager

    # notify the time frame's evaluator task manager to refresh its data
    def _refresh_data(self, time_frame, limit=None):
        evaluator_thread_manager_to_notify = self.evaluator_threads_manager_by_time_frame[time_frame]

        numpy_candle_data = copy.deepcopy(evaluator_thread_manager_to_notify.exchange.get_symbol_prices(
            evaluator_thread_manager_to_notify.symbol,
            evaluator_thread_manager_to_notify.time_frame,
            limit=limit,
            return_list=False))

        evaluator_thread_manager_to_notify.evaluator.set_data(numpy_candle_data)
        self.refreshed_times[time_frame] += 1
        evaluator_thread_manager_to_notify.notify(self.__class__.__name__)

    def _refresh_time_frame_data(self, time_frame):
        try:
            self._refresh_data(time_frame)
        except Exception as e:
            self.logger.error(f" when refreshing data for time frame {time_frame}: {e}")
            self.logger.exception(e)

    def force_refresh_data(self):
        evaluator_thread_manager = next(iter(self.evaluator_threads_manager_by_time_frame.values()))
        backtesting_enabled = Backtesting.enabled(evaluator_thread_manager.get_evaluator().get_config())
        if not backtesting_enabled:
            time_frames = self.evaluator_threads_manager_by_time_frame.keys()
            for time_frame in time_frames:
                self._refresh_time_frame_data(time_frame)

    def _execute_update(self, symbol, exchange, time_frames, backtesting_enabled):
        now = time.time()

        for time_frame in time_frames:

            # backtesting doesn't need to wait a specific time frame to end to refresh data
            if backtesting_enabled:
                try:
                    if exchange.should_update_data(time_frame, symbol):
                        self._refresh_data(time_frame)
                except BacktestingEndedException as e:
                    self.logger.info(e)
                    self.keep_running = False
                    exchange.end_backtesting(symbol)
                    break

            # if data from this time frame needs an update
            elif now - self.time_frame_last_update[time_frame] \
                    >= TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                self._refresh_time_frame_data(time_frame)

                self.time_frame_last_update[time_frame] = time.time()

        self._update_pause(backtesting_enabled, now)

    # start background refresher
    def run(self):
        exchange = None
        symbol = None
        error = None
        try:
            time_frames = self.evaluator_threads_manager_by_time_frame.keys()

            # sort time frames to update them in order of accuracy
            time_frames = TimeFrameManager.sort_time_frames(time_frames)

            if time_frames:

                # figure out from an evaluator if back testing is running for this symbol
                evaluator_thread_manager = next(iter(self.evaluator_threads_manager_by_time_frame.values()))
                symbol = evaluator_thread_manager.get_symbol()

                # test if we need to initialize backtesting features
                backtesting_enabled = Backtesting.enabled(evaluator_thread_manager.get_evaluator().get_config())
                if backtesting_enabled:
                    exchange = evaluator_thread_manager.exchange.get_exchange()
                    exchange.init_candles_offset(time_frames, symbol)

                # init refreshed_times at 0 for each time frame
                self.refreshed_times = {key: 0 for key in time_frames}

                # init last refresh times at 0 for each time frame
                self.time_frame_last_update = {key: 0 for key in time_frames}

                while self.keep_running:
                    self._execute_update(symbol, exchange, time_frames, backtesting_enabled)
            else:
                self.logger.warning("no time frames to monitor, going to sleep.")

        except Exception as e:
            self.logger.exception(e)
            if self.watcher is not None:
                error = e

        finally:
            if exchange is not None and symbol is not None and not exchange.get_backtesting().get_is_finished(symbol):
                if error is None:
                    error = "backtesting did not finish properly."
                self.watcher.set_error(error)

    # calculate task sleep between each refresh
    def _update_pause(self, backtesting_enabled, now):
        if not backtesting_enabled:
            sleeping_time = UPDATER_MAX_SLEEPING_TIME - (time.time() - now)
            if sleeping_time > 0:
                time.sleep(sleeping_time)
        else:
            while not self.ensure_finished_other_threads_tasks():
                time.sleep(0.001)

    # currently used only during backtesting, will force refresh of each supervised task
    def ensure_finished_other_threads_tasks(self):
        for evaluator_thread_manager in self.evaluator_threads_manager_by_time_frame.values():
            symbol_evaluator = evaluator_thread_manager.symbol_evaluator
            if symbol_evaluator.get_deciders_are_busy():
                return False
            else:
                for trader_simulators in symbol_evaluator.trader_simulators.values():
                    trader_simulators.order_manager.force_update_order_status(simulated_time=True)
        return True

    def stop(self):
        self.keep_running = False

    def get_refreshed_times(self, time_frame):
        return self.refreshed_times[time_frame]

    def set_watcher(self, watcher):
        self.watcher = watcher
