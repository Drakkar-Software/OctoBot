import inspect
import logging

from config.cst import EvaluatorMatrixTypes, CONFIG_TRADER_MODE, CONFIG_TRADER
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_matrix import EvaluatorMatrix
from trading.trader import modes


class SymbolEvaluator:
    def __init__(self, config, symbol, crypto_currency_evaluator):
        self.crypto_currency_evaluator = crypto_currency_evaluator
        self.symbol = symbol
        self.trader_simulator = None
        self.config = config
        self.traders = None
        self.trader_simulators = None
        self.logger = logging.getLogger("{0} {1}".format(self.symbol, self.__class__.__name__))

        self.evaluator_thread_managers = {}
        self.trading_mode_instances = {}
        self.matrices = {}
        self.strategies_eval_lists = {}
        self.finalize_enabled_list = {}

        self.trading_mode_class = self.get_trading_mode_class()

    def set_traders(self, trader):
        self.traders = trader

    def set_trader_simulators(self, simulator):
        self.trader_simulators = simulator

    def get_trading_mode_class(self):
        if CONFIG_TRADER in self.config and CONFIG_TRADER_MODE in self.config[CONFIG_TRADER]:
            if any(m[0] == self.config[CONFIG_TRADER][CONFIG_TRADER_MODE] for m in inspect.getmembers(modes)):
                return getattr(modes, self.config[CONFIG_TRADER][CONFIG_TRADER_MODE])

        raise Exception("Please specify a valid trading mode in your config file (trader -> mode)")

    def add_evaluator_thread_manager(self, exchange, symbol, time_frame, evaluator_thread):
        if exchange.get_name() in self.evaluator_thread_managers:
            self.evaluator_thread_managers[exchange.get_name()][time_frame] = evaluator_thread
        else:
            self.evaluator_thread_managers[exchange.get_name()] = {time_frame: evaluator_thread}

            # TODO use config
            self.trading_mode_instances[exchange.get_name()] = self.trading_mode_class(self.config, self, exchange,
                                                                                       symbol)

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
            self.trading_mode_instances[exchange.get_name()].get_decider().add_to_queue()

    def _check_finalize(self, exchange):
        self.finalize_enabled_list[exchange.get_name()] = True
        for evaluator_thread in self.evaluator_thread_managers[exchange.get_name()].values():
            if evaluator_thread.get_refreshed_times() == 0:
                self.finalize_enabled_list[exchange.get_name()] = False

    def get_trader(self, exchange):
        return self.traders[exchange.get_name()]

    def get_trader_simulator(self, exchange):
        return self.trader_simulators[exchange.get_name()]

    def get_final(self, exchange):
        return self.trading_mode_instances[exchange.get_name()].get_decider()

    def has_exchange(self, exchange):
        return exchange.get_name() in self.trading_mode_instances

    def get_matrix(self, exchange):
        return self.matrices[exchange.get_name()]

    def get_evaluator_thread_managers(self, exchange):
        return self.evaluator_thread_managers[exchange.get_name()]

    def get_config(self):
        return self.config

    def get_strategies_eval_list(self, exchange):
        return self.strategies_eval_lists[exchange.get_name()]

    def get_evaluator_order_creator(self, exchange):
        return self.trading_mode_instances[exchange.get_name()].get_creator()

    def get_symbol(self):
        return self.symbol

    def get_crypto_currency_evaluator(self):
        return self.crypto_currency_evaluator
