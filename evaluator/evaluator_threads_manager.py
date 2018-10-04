from tools.logging.logging_util import get_logger

from config.cst import CONFIG_EVALUATORS_WILDCARD, EvaluatorMatrixTypes, START_PENDING_EVAL_NOTE, \
    CONFIG_SAVE_EVALUATION
from evaluator.evaluator import Evaluator
from tools.exporter import MatrixExporter

"""
This class represent the last level of evaluator management by :
- Providing a link between evaluators and symbol evaluation matrix (through notifications)
- Refreshing matrix with evaluators eval_note
"""


class EvaluatorThreadsManager:
    def __init__(self, config,
                 time_frame,
                 symbol_time_frame_updater_thread,
                 symbol_evaluator,
                 exchange,
                 trading_mode,
                 real_time_ta_eval_list,
                 relevant_evaluators=CONFIG_EVALUATORS_WILDCARD):

        self.config = config
        self.exchange = exchange
        self.trading_mode = trading_mode
        self.symbol = symbol_evaluator.get_symbol()
        self.time_frame = time_frame
        self.symbol_time_frame_updater_thread = symbol_time_frame_updater_thread
        self.symbol_evaluator = symbol_evaluator

        self.should_save_evaluations = CONFIG_SAVE_EVALUATION in self.config and self.config[CONFIG_SAVE_EVALUATION]

        # notify symbol evaluator
        self.symbol_evaluator.add_evaluator_thread_manager(self.exchange, self.time_frame, self.trading_mode, self)

        self.matrix = self.symbol_evaluator.get_matrix(self.exchange)
        self.matrix_exporter = MatrixExporter(self.matrix, self.symbol)

        self.thread_name = f"TA THREAD MANAGER - {self.symbol} - {self.exchange.get_name()} - {self.time_frame}"
        self.logger = get_logger(self.thread_name)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_exchange(self.exchange)
        self.evaluator.set_symbol_evaluator(self.symbol_evaluator)

        # Add threaded evaluators that can notify the current thread
        self.evaluator.set_social_eval(self.symbol_evaluator.get_crypto_currency_evaluator().get_social_eval_list(),
                                       self)
        self.evaluator.set_real_time_eval(real_time_ta_eval_list, self)

        # Create static evaluators
        self.evaluator.set_ta_eval_list(self.evaluator.get_creator().create_ta_eval_list(self.evaluator,
                                                                                         relevant_evaluators), self)

        # Register in refreshing threads
        self.symbol_time_frame_updater_thread.register_evaluator_thread_manager(self.time_frame, self)

    # handle notifications from evaluators, when notified refresh symbol evaluation matrix
    def notify(self, notifier_name, force_TA_refresh=False):
        if self.get_refreshed_times() > 0:
            self.logger.debug(f"** Notified by {notifier_name} **")
            if force_TA_refresh:
                self.symbol_time_frame_updater_thread.force_refresh_data()
            self._refresh_eval(notifier_name)
        else:
            self.logger.debug(f"Notification by {notifier_name} ignored")

    def _refresh_eval(self, ignored_evaluator=None):
        # update eval
        self.evaluator.update_ta_eval(ignored_evaluator)

        # update matrix
        self.refresh_matrix()

        # update strategies matrix
        self.symbol_evaluator.update_strategies_eval(self.matrix, self.exchange, ignored_evaluator)

        # calculate the final result
        self.symbol_evaluator.finalize(self.exchange)

        # save evaluations if option is activated
        self._save_evaluations_if_necessary()

        self.logger.debug(f"MATRIX : {self.matrix.get_matrix()}")

    def refresh_matrix(self):
        self.matrix = self.symbol_evaluator.get_matrix(self.exchange)

        for ta_eval in self.evaluator.get_ta_eval_list():
            if ta_eval.get_is_active():
                ta_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.get_name(),
                                     ta_eval.get_eval_note(), self.time_frame)
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.get_name(),
                                     START_PENDING_EVAL_NOTE, self.time_frame)

        for social_eval in self.evaluator.get_social_eval_list():
            if social_eval.get_is_active():
                social_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.get_name(),
                                     social_eval.get_eval_note(), None)
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.get_name(),
                                     START_PENDING_EVAL_NOTE)

        for real_time_eval in self.evaluator.get_real_time_eval_list():
            if real_time_eval.get_is_active():
                real_time_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.REAL_TIME, real_time_eval.get_name(),
                                     real_time_eval.get_eval_note())
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.REAL_TIME, real_time_eval.get_name(),
                                     START_PENDING_EVAL_NOTE)

    def _save_evaluations_if_necessary(self):
        if self.should_save_evaluations and self.symbol_evaluator.are_all_timeframes_initialized(self.exchange):
            self.matrix_exporter.save()

    def start_threads(self):
        pass

    def stop_threads(self):
        for thread in self.evaluator.get_real_time_eval_list():
            thread.stop()

    def join_threads(self):
        for thread in self.evaluator.get_real_time_eval_list():
            thread.join()

    def get_refreshed_times(self):
        return self.symbol_time_frame_updater_thread.get_refreshed_times(self.time_frame)

    def get_evaluator(self):
        return self.evaluator

    def get_symbol_time_frame_updater_thread(self):
        return self.symbol_time_frame_updater_thread

    def get_exchange(self):
        return self.exchange

    def get_symbol_evaluator(self):
        return self.symbol_evaluator

    def get_symbol(self):
        return self.symbol
