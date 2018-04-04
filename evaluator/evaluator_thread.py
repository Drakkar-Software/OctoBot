import logging
import threading
import time

from evaluator import *


class EvaluatorThread(threading.Thread):
    def __init__(self, config, symbol, time_frame, exchange, notifier, trader, social_eval_list):
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
        self.evaluator.set_social_eval(social_eval_list)

    def check_notifications(self):
        result = False
        for social_eval_class in self.evaluator.get_social_eval_list():
            if social_eval_class.notify_if_necessary():
                result = True
                break
        return result

    def run(self):
        # run data refresh
        self.data_refresher.start()

        # wait for first data
        while True:
            if self.data_refresher.get_refreshed():
                break

        # first eval --> create_instances
        self.evaluator.ta_eval()

        while True:
            # for Debug purpose
            ta_eval_list_result = []
            for ta_eval in self.evaluator.get_ta_eval_list():
                ta_eval_list_result.append(ta_eval.get_eval_note())

            self.logger.debug("TA EVAL : " + str(ta_eval_list_result))

            social_eval_list_result = []
            for social_eval in self.evaluator.get_social_eval_list():
                social_eval_list_result.append(social_eval.get_eval_note())

            self.logger.debug("Social EVAL : " + str(social_eval_list_result))

            # calculate the final result
            self.evaluator.finalize()
            self.logger.debug("FINAL : " + str(self.evaluator.get_state()))

            # wait refresh time or refresh if notified
            while True:
                # if an evaluator create notification --> re-eval before the next time frame end
                if self.check_notifications():
                    break

                # If data is refreshed --> recalculate
                if self.data_refresher.get_refreshed():
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
        current = self.refreshed
        self.refreshed = False
        return current

    def refresh_data(self):
        self.parent.evaluator.set_data(
            self.parent.exchange.get_symbol_prices(
                self.parent.symbol,
                self.parent.exchange_time_frame(self.parent.time_frame)))
        self.refreshed = True

    def run(self):
        while True:
            self.refresh_data()
            time.sleep(self.parent.time_frame.value * MINUTE_TO_SECONDS)
