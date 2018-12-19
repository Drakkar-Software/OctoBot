from tools.logging.logging_util import get_logger

from backtesting.backtesting import Backtesting
from evaluator.Updaters.social_evaluator_not_threaded_update import SocialEvaluatorNotThreadedUpdateThread
from evaluator.evaluator_creator import EvaluatorCreator
from config import CONFIG_EVALUATORS_WILDCARD


class CryptocurrencyEvaluator:
    def __init__(self, config, crypto_currency, dispatchers_list, relevant_evaluators=None):
        if relevant_evaluators is None:
            relevant_evaluators = CONFIG_EVALUATORS_WILDCARD
        self.config = config
        self.crypto_currency = crypto_currency
        self.dispatchers_list = dispatchers_list

        self.symbol_evaluator_list = {}

        if Backtesting.enabled(self.config):
            self.social_eval_list = []
            self.social_not_threaded_list = []
        else:
            self.social_eval_list = EvaluatorCreator.create_social_eval(self.config,
                                                                        self.crypto_currency,
                                                                        self.dispatchers_list,
                                                                        relevant_evaluators)

            self.social_not_threaded_list = EvaluatorCreator.create_social_not_threaded_list(self.social_eval_list)

        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self.social_not_threaded_list)

    def add_symbol_evaluator(self, symbol, symbol_evaluator):
        self.symbol_evaluator_list[symbol] = symbol_evaluator

    def _activate_deactivate_strategies(self, strategies, exchange, activate=True):
        try:
            for symbol_evaluator in self.symbol_evaluator_list.values():
                symbol_evaluator.activate_deactivate_strategies(strategies, exchange, activate)
        except Exception as e:
            get_logger(self.__class__.__name__).error(f"{self.crypto_currency} error in activate_deactivate_strategies(): {e}")

    def deactivate_strategies(self, strategies, exchange):
        self._activate_deactivate_strategies(strategies, exchange, False)

    def activate_strategies(self, strategies, exchange):
        self._activate_deactivate_strategies(strategies, exchange, True)

    def start_threads(self):
        self.social_evaluator_refresh.start()

    def stop_threads(self):
        for thread in self.social_eval_list:
            thread.stop()

        self.social_evaluator_refresh.stop()

    def join_threads(self):
        for thread in self.social_eval_list:
            if thread.is_alive():
                thread.join()

        self.social_evaluator_refresh.join()

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_dispatchers_list(self):
        return self.dispatchers_list

    def get_social_not_threaded_list(self):
        return self.social_not_threaded_list

    def get_symbol_pairs(self):
        return self.config["crypto_currencies"][self.crypto_currency]["pairs"]

    def get_symbol_evaluator_list(self):
        return self.symbol_evaluator_list

    def get_config(self):
        return self.config
