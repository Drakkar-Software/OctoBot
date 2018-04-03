import logging
import threading
import time

from evaluator import *
from evaluator.evalutionUtil import *


class TAEvaluatorThread(threading.Thread):
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

        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_notifier(self.notifier)
        self.evaluator.set_trader(self.trader)

        self.evaluationMatrix = EvaluationMatrix()

    def get_evaluation_matrix(self):
        return self.evaluationMatrix

    def notify(self, notifier_name):
        self.logger.debug(notifier_name+" notified value: " + str(self.evaluationMatrix.get_social_evals()) + " to: "
                          + self.thread_name)
        self.update_relevant_instant_indicators()
        self.compute_aggregated_values()

    def update_relevant_instant_indicators(self):
        self.update_TAs()

    def update_TAs(self):
        self.evaluator.set_data(self.exchange.get_symbol_prices(self.symbol,
                                                                self.exchange_time_frame(self.time_frame)))

        for TA_eval_class in self.evaluator.ta_eval():
            self.evaluationMatrix.set_TA_eval(TA_eval_class.get_evaluator_name()
                                              , TA_eval_class.get_eval_note())

        self.logger.debug("Updated TA Eval : " + str(self.evaluationMatrix.get_TA_evals()) + " social evals: "
                          + str(self.evaluationMatrix.get_social_evals()))

    def compute_aggregated_values(self):
        self.evaluator.finalize()
        self.logger.debug("FINAL AGGREGATED VALUE: " + str(self.evaluator.get_state()))

    def run(self):
        while True:
            # update every TA
            self.update_TAs()
            self.compute_aggregated_values()
            time.sleep(self.time_frame.value * MINUTE_TO_SECONDS)


class SocialEvaluatorThread(threading.Thread):
    def __init__(self, config, symbol, time_frame, notifier, TA_threads):
        threading.Thread.__init__(self)
        self.config = config
        self.symbol = symbol
        self.notifier = notifier
        self.time_frame = time_frame
        self.TA_threads = TA_threads

        self.thread_name = "SOCIAL THREAD - " + self.symbol
        self.logger = logging.getLogger(self.thread_name)

        self.evaluator = Evaluator()
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)

        self.evaluationMatrix = EvaluationMatrix()

        self.social_threads = []

        for social_eval_class in self.evaluator.social_eval(self.evaluationMatrix, TA_threads):
            self.social_threads.append(social_eval_class)

    def get_evaluation_matrix(self):
        return self.evaluationMatrix

    def notify(self, notifier_name):
        self.logger.warning("SHOULD NOT HAPPEN (social thread got notified): " + notifier_name+" notified value: "
                            + str(self.evaluationMatrix.get_social_evals()) + " to: " + self.thread_name)

    def run(self):
        for thread in self.social_threads:
            thread.start()
