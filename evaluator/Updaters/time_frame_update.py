import threading
import time

from backtesting.backtesting import Backtesting
from config.cst import *


# reset to count sec
class TimeFrameUpdateDataThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.refreshed_times = 0
        self.keep_running = True

    def stop(self):
        self.keep_running = False

    def get_refreshed_times(self):
        return self.refreshed_times

    def _refresh_data(self, limit=None):
        self.parent.evaluator.set_data(
            self.parent.exchange.get_symbol_prices(
                self.parent.symbol,
                self.parent.time_frame,
                limit=limit))
        self.refreshed_times += 1
        self.parent.notify(self.__class__.__name__)

    def run(self):
        while self.keep_running:
            now = time.time()
            self._refresh_data()
            if not Backtesting.enabled(self.parent.get_evaluator().get_config()):
                time.sleep(TimeFramesMinutes[self.parent.time_frame] * MINUTE_TO_SECONDS - (time.time() - now))

