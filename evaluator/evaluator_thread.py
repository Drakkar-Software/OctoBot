import logging
import threading
import time

from evaluator import *


class EvaluatorThread(threading.Thread):
    def __init__(self, config, symbol, time_frame, exchange, notifier, trader):
        threading.Thread.__init__(self)
        self.config = config
        self.exchange = exchange
        self.exchange_time_frame = self.exchange.get_time_frame_enum()
        self.symbol = symbol
        self.time_frame = time_frame
        self.notifier = notifier
        self.trader = trader

        self.thread_name = "TA THREAD - " + self.symbol \
                           + " - " + self.exchange.__class__.__name__ \
                           + " - " + str(self.time_frame)
        self.logger = logging.getLogger(self.thread_name)

        # Create data refresh thread
        self.data_refresher = TimeFrameDataThread(self)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_notifier(self.notifier)
        self.evaluator.set_trader(self.trader)

    def check_notifications(self):
        result = False
        for social_eval_class in self.evaluator.social_eval():
            if social_eval_class.need_to_notify:
                result = True
                break
        return result

    def run(self):
        # run data refresh
        self.data_refresher.start()

        while True:

            # If data is beeing refreshed wait
            if not self.data_refresher.get_refreshed():
                continue

            self.evaluator.finalize()
            self.logger.debug("FINAL : " + str(self.evaluator.get_state()))

            # wait refresh time or refresh if notified
            while True:
                # if an evaluator create notification --> re-eval before the next time frame end
                if self.check_notifications():
                    break
                time.sleep(1)


# reset to count sec
# At the end of a time frame --> update time frame depending data
class TimeFrameDataThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.refreshed = False

    def get_refreshed(self):
        return self.refreshed

    def refresh_data(self):
        self.refreshed = False
        self.parent.evaluator.set_data(
            self.parent.exchange.get_symbol_prices(
                self.parent.symbol,
                self.parent.exchange_time_frame(self.parent.time_frame)))
        self.refreshed = True

    def run(self):
        while True:
            self.refresh_data()
            time.sleep(self.parent.time_frame.value * MINUTE_TO_SECONDS)
