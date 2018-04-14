from config.cst import EvaluatorMatrixTypes
from evaluator.Updaters.social_evaluator_not_threaded_update import SocialEvaluatorNotThreadedUpdateThread
from evaluator.Updaters.social_global_updater import SocialGlobalUpdaterThread
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_final import FinalEvaluator
from evaluator.evaluator_matrix import EvaluatorMatrix
from evaluator.evaluator_order_creator import EvaluatorOrderCreator


class Symbol_Evaluator:
    def __init__(self, config, crypto_currency, dispatchers_list):
        self.crypto_currency = crypto_currency
        self.trader_simulator = None
        self.config = config
        self.notifier = None
        self.traders = None
        self.trader_simulators = None
        self.finalize_enabled = False
        self.dispatchers_list = dispatchers_list

        self.evaluator_threads = []

        self.matrix = EvaluatorMatrix()

        self.social_eval_list = EvaluatorCreator.create_social_eval(self.config, self.crypto_currency, self.dispatchers_list)
        self.social_not_threaded_list = EvaluatorCreator.create_social_not_threaded_list(self.social_eval_list)
        self.strategies_eval_list = EvaluatorCreator.create_strategies_eval_list()

        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self.social_not_threaded_list)
        self.global_social_updater = SocialGlobalUpdaterThread(self)
        self.evaluator_order_creator = EvaluatorOrderCreator()
        self.final_evaluator = FinalEvaluator(self)

    def start_threads(self):
        self.social_evaluator_refresh.start()
        self.global_social_updater.start()

    def stop_threads(self):
        for thread in self.social_eval_list:
            thread.stop()

        self.social_evaluator_refresh.stop()
        self.global_social_updater.stop()

    def join_threads(self):
        for thread in self.social_eval_list:
            thread.join()

        self.social_evaluator_refresh.join()
        self.global_social_updater.join()

    def set_notifier(self, notifier):
        self.notifier = notifier

    def set_traders(self, trader):
        self.traders = trader

    def set_trader_simulators(self, simulator):
        self.trader_simulators = simulator

    def add_evaluator_thread(self, evaluator_thread):
        self.evaluator_threads.append(evaluator_thread)

    def update_strategies_eval(self, new_matrix, ignored_evaluator=None):
        for strategies_evaluator in self.strategies_eval_list:
            strategies_evaluator.set_matrix(new_matrix)
            if not strategies_evaluator.get_name() == ignored_evaluator and strategies_evaluator.get_is_evaluable():
                strategies_evaluator.eval()

            # update matrix
            self.matrix.set_eval(EvaluatorMatrixTypes.STRATEGIES, strategies_evaluator.get_name(),
                                 strategies_evaluator.get_eval_note())

    def finalize(self, exchange, symbol):
        if not self.finalize_enabled:
            self.check_finalize()

        if self.finalize_enabled:
            self.final_evaluator.add_to_queue(exchange, symbol)

    def check_finalize(self):
        self.finalize_enabled = True
        for evaluator_thread in self.evaluator_threads:
            if evaluator_thread.get_data_refresher().get_refreshed_times() == 0:
                self.finalize_enabled = False

    def get_notifier(self):
        return self.notifier

    def get_trader(self, exchange):
        return self.traders[exchange.get_name()]

    def get_trader_simulator(self, exchange):
        return self.trader_simulators[exchange.get_name()]

    def get_final(self):
        return self.final_evaluator

    def get_matrix(self):
        return self.matrix

    def get_evaluator_creator(self):
        return self.evaluator_order_creator

    def get_strategies_eval_list(self):
        return self.strategies_eval_list

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_dispatchers_list(self):
        return self.dispatchers_list

    def get_social_not_threaded_list(self):
        return self.social_not_threaded_list

    def get_symbol_pairs(self):
        return self.config["crypto_currencies"][self.crypto_currency]["pairs"]

