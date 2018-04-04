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
        self.time_before_next_time_frame = 0
        self.social_eval_value_list = []
        self.TA_eval_value_list = []

        self.thread_name = "TA THREAD - " + self.symbol \
                           + " - " + self.exchange.__class__.__name__ \
                           + " - " + str(self.time_frame)
        self.logger = logging.getLogger(self.thread_name)

        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_notifier(self.notifier)
        self.evaluator.set_trader(self.trader)

    def reset_eval_lists(self):
        self.social_eval_value_list = []
        self.TA_eval_value_list = []

    # reset to count sec
    def reset_time_before_next_time_frame(self):
        self.time_before_next_time_frame = self.time_frame.value * MINUTE_TO_SECONDS

    def check_notifications(self):
        result = False
        for social_eval_class in self.evaluator.social_eval():
            if social_eval_class.need_to_notify:
                result = True
                break
        return result

    def run(self):
        self.reset_time_before_next_time_frame()
        while True:
            self.evaluator.set_data(self.exchange.get_symbol_prices(self.symbol,
                                                                    self.exchange_time_frame(self.time_frame)))

            self.reset_eval_lists()

            # show eval list
            # Get the current evals of each social indicators (no need to get new data)
            for social_eval_class in self.evaluator.social_eval():
                self.social_eval_value_list.append(social_eval_class.get_eval_note())

            # Get the current evals of each TA indicators (no need to get new data)
            for TA_eval_class in self.evaluator.ta_eval():
                self.TA_eval_value_list.append(TA_eval_class.get_eval_note())

            self.logger.debug("Social Eval : " + str(self.social_eval_value_list))
            self.logger.debug("TA Eval : " + str(self.TA_eval_value_list))

            self.evaluator.finalize()
            self.logger.debug("FINAL : " + str(self.evaluator.get_state()))

            # wait refresh time or refresh if notified
            while self.time_before_next_time_frame > 0:
                self.time_before_next_time_frame -= 1
                time.sleep(1)

                # if an evaluator create notification --> re-eval before the next time frame end
                if self.check_notifications():
                    break

            if self.time_before_next_time_frame == 0:
                self.reset_time_before_next_time_frame()
