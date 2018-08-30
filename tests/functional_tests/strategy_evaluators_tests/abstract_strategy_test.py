from abc import ABCMeta
import copy

from backtesting.backtesting_util import create_backtesting_config, create_backtesting_bot, \
    start_backtesting_bot, filter_wanted_symbols
from backtesting.abstract_backtesting_test import AbstractBacktestingTest
from config.cst import CONFIG_EVALUATOR, CONFIG_BACKTESTING, CONFIG_BACKTESTING_DATA_FILES
from evaluator import Strategies
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from tools.class_inspector import get_class_from_string, evaluator_parent_inspection
from backtesting.collector.data_file_manager import interpret_file_name, DATA_FILE_EXT
from tests.test_utils.config import load_test_config
from services.web_service import WebService


DEFAULT_SYMBOL = "ICX/BTC"
DATA_FILE_PATH = "tests/static/"


class AbstractStrategyTest(AbstractBacktestingTest):
    __metaclass__ = ABCMeta

    def init(self, strategy_evaluator_class, config=None):
        if config is None:
            self.config = create_backtesting_config(load_test_config(), filter_symbols=False)
        else:
            self.config = config
        self.strategy_evaluator_class = strategy_evaluator_class
        self._register_only_strategy(strategy_evaluator_class)
        self._assert_init()

    def _assert_results(self, run_results, profitability, bot):
        # print(f"results: {run_results} expected: {profitability}")  # convenient for building tests
        assert run_results[0] >= profitability

    def _run_backtesting_with_current_config(self, symbol, data_file_to_use=None):
        config_to_use = copy.deepcopy(self.config)
        if data_file_to_use is not None:
            for index, datafile in enumerate(config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES]):
                _, file_symbol, _ = interpret_file_name(datafile)
                if symbol == file_symbol:
                    config_to_use[CONFIG_BACKTESTING][CONFIG_BACKTESTING_DATA_FILES][index] = \
                        DATA_FILE_PATH + data_file_to_use + DATA_FILE_EXT

        # do not activate web interface on standalone backtesting bot
        WebService.enable(config_to_use, False)
        filter_wanted_symbols(config_to_use, [symbol])
        bot = create_backtesting_bot(config_to_use)
        return start_backtesting_bot(bot), bot

    def _register_only_strategy(self, strategy_evaluator_class):
        for evaluatotor_name in self.config[CONFIG_EVALUATOR]:
            if get_class_from_string(evaluatotor_name, StrategiesEvaluator, Strategies,
                                     evaluator_parent_inspection) is not None:
                self.config[CONFIG_EVALUATOR][evaluatotor_name] = False
        self.config[CONFIG_EVALUATOR][strategy_evaluator_class.get_name()] = True

    def _assert_init(self):
        assert self.config
        assert self.config[CONFIG_EVALUATOR][self.strategy_evaluator_class.get_name()] is True
