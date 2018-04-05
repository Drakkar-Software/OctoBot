import logging
import threading
import time

from config.cst import *
from evaluator.evaluator import Evaluator
from evaluator.evaluator_matrix import EvaluatorMatrix


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

        self.matrix = EvaluatorMatrix()

        self.thread_name = "TA THREAD - " + self.symbol \
                           + " - " + self.exchange.__class__.__name__ \
                           + " - " + str(self.time_frame)
        self.logger = logging.getLogger(self.thread_name)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_notifier(self.notifier)
        self.evaluator.set_trader(self.trader)
        self.evaluator.set_social_eval(social_eval_list, self)

        # Create refreshing threads
        self.data_refresher = TimeFrameUpdateDataThread(self)
        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self)

    def notify(self, notifier_name):
        self.logger.debug("Notified by " + notifier_name)
        self.refresh_eval()

    def refresh_eval(self):
        # First eval --> create_instances
        # Instances will be created only if they don't already exist
        self.evaluator.create_ta_eval()

        # update eval
        self.evaluator.update_ta_eval()

        # for Debug purpose
        ta_eval_list_result = []
        for ta_eval in self.evaluator.get_ta_eval_list():
            result = ta_eval.get_eval_note()
            ta_eval_list_result.append(result)
            self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.__class__.__name__, result)

        self.logger.debug("TA EVAL : " + str(ta_eval_list_result))

        social_eval_list_result = []
        for social_eval in self.evaluator.get_social_eval_list():
            result = social_eval.get_eval_note()
            social_eval_list_result.append(result)
            self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.__class__.__name__, result)

        self.logger.debug("Social EVAL : " + str(social_eval_list_result))

        # calculate the final result
        self.evaluator.finalize()
        self.logger.debug("FINAL : " + str(self.evaluator.get_state()))
        self.logger.debug("MATRIX : " + str(self.matrix.get_matrix()))

    def run(self):
        # Start refresh threads
        self.data_refresher.start()
        self.social_evaluator_refresh.start()
        self.data_refresher.join()
        self.social_evaluator_refresh.join()


# reset to count sec
# At the end of a time frame --> update time frame depending data
# Bug issue : https://github.com/Trading-Bot/CryptoBot/issues/38
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


class SocialEvaluatorNotThreadedUpdateThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.social_evaluator_list = self.parent.evaluator.create_social_not_threaded_list()
        self.social_evaluator_list_timers = []
        self.get_eval_timers()

    def get_eval_timers(self):
        for social_eval in self.social_evaluator_list:
            # if key exists --> else this social eval will not be refreshed
            if SOCIAL_CONFIG_REFRESH_RATE in social_eval.get_social_config():
                self.social_evaluator_list_timers.append(
                    {
                        "social_evaluator_class_inst": social_eval,
                        "refresh_rate": social_eval.get_social_config()[SOCIAL_CONFIG_REFRESH_RATE],
                        # force first refresh
                        "last_refresh": social_eval.get_social_config()[SOCIAL_CONFIG_REFRESH_RATE],
                        "last_refresh_time": time.time()
                    })
            else:
                self.parent.logger.warn("Social evaluator " + social_eval.__class__.__name__
                                        + " doesn't have a valid social config refresh rate.")

    def run(self):
        while True:
            for social_eval in self.social_evaluator_list_timers:
                now = time.time()
                social_eval["last_refresh"] += now - social_eval["last_refresh_time"]
                social_eval["last_refresh_time"] = now
                if social_eval["last_refresh"] >= social_eval["refresh_rate"]:
                    social_eval["last_refresh"] = 0
                    social_eval["social_evaluator_class_inst"].eval()
                    self.parent.logger.debug(social_eval["social_evaluator_class_inst"].__class__.__name__
                                             + " refreshed by generic social refresher thread after "
                                             + str(social_eval["refresh_rate"]) + "sec")

            time.sleep(1)
