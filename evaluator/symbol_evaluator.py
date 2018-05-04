from config.cst import EvaluatorMatrixTypes
from evaluator.Updaters.social_evaluator_not_threaded_update import SocialEvaluatorNotThreadedUpdateThread
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_final import FinalEvaluator
from evaluator.evaluator_matrix import EvaluatorMatrix
from evaluator.evaluator_order_creator import EvaluatorOrderCreator
from backtesting.backtesting import Backtesting


class SymbolEvaluator:
    def __init__(self, config, crypto_currency, dispatchers_list):
        self.crypto_currency = crypto_currency
        self.trader_simulator = None
        self.config = config
        self.traders = None
        self.trader_simulators = None
        self.dispatchers_list = dispatchers_list

        self.evaluator_thread_managers = {}
        self.final_evaluators = {}
        self.matrices = {}
        self.strategies_eval_lists = {}
        self.finalize_enabled_list = {}

        if Backtesting.enabled(self.config):
            self.social_eval_list = []
            self.social_not_threaded_list = []
        else:
            self.social_eval_list = EvaluatorCreator.create_social_eval(self.config,
                                                                        self.crypto_currency,
                                                                        self.dispatchers_list)

            self.social_not_threaded_list = EvaluatorCreator.create_social_not_threaded_list(self.social_eval_list)

        self.social_evaluator_refresh = SocialEvaluatorNotThreadedUpdateThread(self.social_not_threaded_list)

        self.evaluator_order_creator = EvaluatorOrderCreator()

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

    def set_traders(self, trader):
        self.traders = trader

    def set_trader_simulators(self, simulator):
        self.trader_simulators = simulator

    def add_evaluator_thread_manager(self, exchange, symbol, evaluator_thread):
        if exchange.get_name() in self.evaluator_thread_managers:
            self.evaluator_thread_managers[exchange.get_name()].append(evaluator_thread)
        else:
            self.evaluator_thread_managers[exchange.get_name()] = [evaluator_thread]
            self.final_evaluators[exchange.get_name()] = FinalEvaluator(self, exchange, symbol)
            self.matrices[exchange.get_name()] = EvaluatorMatrix(self.config)
            self.strategies_eval_lists[exchange.get_name()] = EvaluatorCreator.create_strategies_eval_list(self.config)
            self.finalize_enabled_list[exchange.get_name()] = False

    def update_strategies_eval(self, new_matrix, exchange, ignored_evaluator=None):
        for strategies_evaluator in self.get_strategies_eval_list(exchange):
            strategies_evaluator.set_matrix(new_matrix)
            if not strategies_evaluator.get_name() == ignored_evaluator and strategies_evaluator.get_is_evaluable():
                strategies_evaluator.eval()

            new_matrix.set_eval(EvaluatorMatrixTypes.STRATEGIES, strategies_evaluator.get_name(),
                                strategies_evaluator.get_eval_note())

    def finalize(self, exchange):
        if not self.finalize_enabled_list[exchange.get_name()]:
            self._check_finalize(exchange)

        if self.finalize_enabled_list[exchange.get_name()]:
            self.final_evaluators[exchange.get_name()].add_to_queue()

    def _check_finalize(self, exchange):
        self.finalize_enabled_list[exchange.get_name()] = True
        for evaluator_thread in self.evaluator_thread_managers[exchange.get_name()]:
            if evaluator_thread.get_refreshed_times() == 0:
                self.finalize_enabled_list[exchange.get_name()] = False

    def get_trader(self, exchange):
        return self.traders[exchange.get_name()]

    def get_trader_simulator(self, exchange):
        return self.trader_simulators[exchange.get_name()]

    def get_final(self, exchange):
        return self.final_evaluators[exchange.get_name()]

    def get_matrix(self, exchange):
        return self.matrices[exchange.get_name()]

    def get_evaluator_thread_managers(self, exchange):
        return self.evaluator_thread_managers[exchange.get_name()]

    def get_config(self):
        return self.config

    def get_strategies_eval_list(self, exchange):
        return self.strategies_eval_lists[exchange.get_name()]

    def get_evaluator_order_creator(self):
        return self.evaluator_order_creator

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_dispatchers_list(self):
        return self.dispatchers_list

    def get_social_not_threaded_list(self):
        return self.social_not_threaded_list

    def get_symbol_pairs(self):
        return self.config["crypto_currencies"][self.crypto_currency]["pairs"]

