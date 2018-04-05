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
        self.data_refresher = TimeFrameUpdateDataThread(self)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_notifier(self.notifier)
        self.evaluator.set_trader(self.trader)
        self.evaluator.set_social_eval(social_eval_list, self)

    def notify(self, notifier_name):
        self.logger.debug("Notified by " + notifier_name)
        self.refresh_eval()

    def refresh_eval(self):
        # First eval --> create_instances
        # Instances will be created only if they don't already exist
        self.evaluator.create_social_eval()
        self.evaluator.create_ta_eval()

        # update eval
        self.evaluator.update_ta_eval()

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

    def run(self):
        # run data refresh
        self.data_refresher.start()
        self.data_refresher.join()

# reset to count sec
# At the end of a time frame --> update time frame depending data
class TimeFrameUpdateDataThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def refresh_data(self):
        self.parent.evaluator.set_data(
            self.parent.exchange.get_symbol_prices(
                self.parent.symbol,
                self.parent.exchange_time_frame(self.parent.time_frame)))
        self.parent.notify(self.__class__.__name__)

    def run(self):
        while True:
            self.refresh_data()
            time.sleep(self.parent.time_frame.value * MINUTE_TO_SECONDS)
