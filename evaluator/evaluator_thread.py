import logging
import pprint
import threading

from config.cst import *
from evaluator.evaluator import Evaluator
from evaluator.evaluator_matrix import EvaluatorMatrix
from evaluator.Updaters.social_evaluator_not_threaded_update import SocialEvaluatorNotThreadedUpdateThread
from evaluator.Updaters.time_frame_update import TimeFrameUpdateDataThread


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
        self.evaluator.get_creator().set_social_eval(social_eval_list, self)

        # Create refreshing threads
        self.data_refresher = TimeFrameUpdateDataThread(self)
        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self)

    def notify(self, notifier_name):
        if self.data_refresher.get_refreshed_times() > 0:
            self.logger.debug("** Notified by " + notifier_name + " **")
            self.refresh_eval(notifier_name)
        else:
            self.logger.debug("Notification by " + notifier_name + " ignored")

    def refresh_eval(self, ignored_evaluator=None):
        # First eval --> create_instances
        # Instances will be created only if they don't already exist
        self.evaluator.get_creator().create_ta_eval()

        # update eval
        self.evaluator.update_ta_eval(ignored_evaluator)

        # update matrix
        for ta_eval in self.evaluator.get_creator().get_ta_eval_list():
            self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.__class__.__name__,
                                 ta_eval.get_eval_note())

        for social_eval in self.evaluator.get_creator().get_social_eval_list():
            self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.__class__.__name__,
                                 social_eval.get_eval_note())

        # calculate the final result
        self.evaluator.finalize()
        self.logger.debug("--> " + str(self.evaluator.get_final().get_state()))
        self.logger.debug("MATRIX : " + pprint.pformat(self.matrix.get_matrix()))

    def run(self):
        # Start refresh threads
        self.data_refresher.start()
        self.social_evaluator_refresh.start()
        self.data_refresher.join()
        self.social_evaluator_refresh.join()
