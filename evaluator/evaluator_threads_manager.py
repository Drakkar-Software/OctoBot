import logging

from config.cst import *
from evaluator.Updaters.time_frame_update import TimeFrameUpdateDataThread
from evaluator.evaluator import Evaluator


class EvaluatorThreadsManager:
    def __init__(self, config,
                 symbol,
                 time_frame,
                 symbol_evaluator,
                 exchange,
                 real_time_ta_eval_list):
        self.config = config
        self.symbol = symbol
        self.time_frame = time_frame
        self.symbol_evaluator = symbol_evaluator

        # notify symbol evaluator
        self.symbol_evaluator.add_evaluator_thread(self)

        self.matrix = self.symbol_evaluator.get_matrix()

        # Exchange
        self.exchange = exchange
        # TODO : self.exchange.update_balance(self.symbol)

        self.thread_name = "TA THREAD - {0} - {1} - {2}".format(self.symbol,
                                                                self.exchange.__class__.__name__,
                                                                self.time_frame)
        self.logger = logging.getLogger(self.thread_name)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_exchange(self.exchange)
        self.evaluator.set_symbol_evaluator(self.symbol_evaluator)

        # Add threaded evaluators that can notify the current thread
        self.evaluator.set_social_eval(self.symbol_evaluator.get_social_eval_list(), self)
        self.evaluator.set_real_time_eval(real_time_ta_eval_list, self)
        self.evaluator.set_ta_eval_list(self.evaluator.get_creator().create_ta_eval_list(self.evaluator))

        # Create refreshing threads
        self.data_refresher = TimeFrameUpdateDataThread(self)

    def notify(self, notifier_name):
        if self.data_refresher.get_refreshed_times() > 0:
            self.logger.debug("** Notified by {0} **".format(notifier_name))
            self.refresh_eval(notifier_name)
        else:
            self.logger.debug("Notification by {0} ignored".format(notifier_name))

    def refresh_eval(self, ignored_evaluator=None):
        # update eval
        self.evaluator.update_ta_eval(ignored_evaluator)

        # update matrix
        self.refresh_matrix()

        # update strategies matrix
        self.symbol_evaluator.update_strategies_eval(self.matrix, ignored_evaluator)

        # calculate the final result
        self.symbol_evaluator.finalize(self.exchange, self.symbol)
        self.logger.debug("MATRIX : {0}".format(self.matrix.get_matrix()))

    def refresh_matrix(self):
        self.matrix = self.symbol_evaluator.get_matrix()

        for ta_eval in self.evaluator.get_ta_eval_list():
            self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.get_name(),
                                 ta_eval.get_eval_note(), self.time_frame)

        for social_eval in self.evaluator.get_social_eval_list():
            self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.get_name(),
                                 social_eval.get_eval_note())

        for real_time_eval in self.evaluator.get_real_time_eval_list():
            self.matrix.set_eval(EvaluatorMatrixTypes.REAL_TIME, real_time_eval.get_name(),
                                 real_time_eval.get_eval_note())

    def start_threads(self):
        self.data_refresher.start()

    def stop_threads(self):
        for thread in self.evaluator.get_real_time_eval_list():
            thread.stop()
        self.data_refresher.stop()

    def join_threads(self):
        for thread in self.evaluator.get_real_time_eval_list():
            thread.join()
        self.data_refresher.join()

    def get_data_refresher(self):
        return self.data_refresher
