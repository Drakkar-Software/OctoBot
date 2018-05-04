from backtesting.backtesting import Backtesting
from evaluator.Updaters.social_evaluator_not_threaded_update import SocialEvaluatorNotThreadedUpdateThread
from evaluator.evaluator_creator import EvaluatorCreator


class CryptocurrencyEvaluator:
    def __init__(self, config, crypto_currency, dispatchers_list):
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
                                                                        self.dispatchers_list)

            self.social_not_threaded_list = EvaluatorCreator.create_social_not_threaded_list(self.social_eval_list)

        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self.social_not_threaded_list)

    def add_symbol_evaluator(self, symbol, symbol_evaluator):
        self.symbol_evaluator_list[symbol] = symbol_evaluator

    def start_threads(self):
        self.social_evaluator_refresh.start()

    def stop_threads(self):
        for thread in self.social_eval_list:
            thread.stop()

        self.social_evaluator_refresh.stop()

    def join_threads(self):
        for thread in self.social_eval_list:
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
