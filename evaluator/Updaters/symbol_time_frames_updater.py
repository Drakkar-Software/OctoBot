import threading
import time
import logging

from backtesting.backtesting import Backtesting
from config.cst import *


class SymbolTimeFramesDataUpdaterThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.evaluator_threads_manager_by_time_frame = {}
        self.refreshed_times = {}
        self.time_frame_last_update = {}
        self.keep_running = True

    # add a time frame to watch and its related evaluator thread manager
    def register_evaluator_thread_manager(self, time_frame, evaluator_thread_manager):
        self.evaluator_threads_manager_by_time_frame[time_frame] = evaluator_thread_manager

    def stop(self):
        self.keep_running = False

    def get_refreshed_times(self, time_frame):
        return self.refreshed_times[time_frame]

    # notify the time frame's evaluator thread manager to refresh its data
    def _refresh_data(self, time_frame, limit=None):
        evaluator_thread_manager_to_notify = self.evaluator_threads_manager_by_time_frame[time_frame]
        evaluator_thread_manager_to_notify.evaluator.set_data(
            evaluator_thread_manager_to_notify.exchange.get_symbol_prices(
                evaluator_thread_manager_to_notify.symbol,
                evaluator_thread_manager_to_notify.time_frame,
                limit=limit))
        self.refreshed_times[time_frame] += 1
        evaluator_thread_manager_to_notify.notify(self.__class__.__name__)

    # start background refresher
    def run(self):
        time_frames = self.evaluator_threads_manager_by_time_frame.keys()

        if time_frames:
            max_sleeping_time = 2

            # figure out from an evaluator if back testing is running for this symbol
            evaluator_thread_manager = next(iter(self.evaluator_threads_manager_by_time_frame.values()))
            back_testing_enabled = Backtesting.enabled(evaluator_thread_manager.get_evaluator().get_config())

            # init refreshed_times at 0 for each time frame
            self.refreshed_times = {key: 0 for key in time_frames}
            # init last refresh times at 0 for each time frame
            self.time_frame_last_update = {key: 0 for key in time_frames}

            while self.keep_running:
                now = time.time()

                for time_frame in time_frames:
                    if back_testing_enabled:
                        if evaluator_thread_manager.exchange.get_exchange().should_update_data(time_frame):
                            self._refresh_data(time_frame)

                    # if data from this time frame needs an update
                    elif now - self.time_frame_last_update[time_frame] >= \
                            TimeFramesMinutes[time_frame] * MINUTE_TO_SECONDS:
                        self._refresh_data(time_frame)
                        self.time_frame_last_update[time_frame] = time.time()

                if not back_testing_enabled:
                    sleeping_time = max_sleeping_time - (time.time() - now)
                    if sleeping_time > 0:
                        time.sleep(sleeping_time)
                else:
                    time.sleep(1)
        else:
            logging.getLogger(self.__class__.__name__).warning("no time frames to monitor, going to sleep.")
