import threading
import time

from config.cst import *


# reset to count sec
# At the end of a time frame --> update time frame depending data
# Bug issue : https://github.com/Trading-Bot/CryptoBot/issues/38
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

    def refresh_data(self):
        self.parent.evaluator.set_data(
            self.parent.exchange.get_symbol_prices(
                self.parent.symbol,
                self.parent.exchange_time_frame(self.parent.time_frame)))
        self.refreshed_times += 1
        self.parent.notify(self.__class__.__name__)

    def run(self):
        while self.keep_running:
            now = time.time()
            self.refresh_data()
            time.sleep(self.parent.time_frame.value * MINUTE_TO_SECONDS - (time.time() - now))
