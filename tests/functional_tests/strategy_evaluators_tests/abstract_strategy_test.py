#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
from abc import ABCMeta, ABC
import copy

from octobot.backtesting.abstract_backtesting_test import AbstractBacktestingTest
from octobot.api.backtesting import get_independent_backtesting_exchange_manager_ids, \
    create_independent_backtesting, initialize_and_run_independent_backtesting, join_independent_backtesting
from octobot_commons.constants import CONFIG_WILDCARD
from octobot_commons.logging.logging_util import get_logger
from octobot_commons.tentacles_management.class_inspector import get_class_from_string, evaluator_parent_inspection, \
    trading_mode_parent_inspection
from octobot_commons.tests.test_config import load_test_config
from octobot_evaluators.evaluator import StrategyEvaluator
from octobot_tentacles_manager.api.configurator import update_activation_configuration, get_tentacles_activation
from octobot_tentacles_manager.constants import TENTACLES_EVALUATOR_PATH, TENTACLES_TRADING_PATH
from octobot_trading.api.exchange import get_exchange_managers_from_exchange_ids
from octobot_trading.api.profitability import get_profitability_stats
from octobot_trading.constants import CONFIG_SIMULATOR_FEES_TAKER, CONFIG_SIMULATOR_FEES_MAKER, CONFIG_SIMULATOR_FEES, \
    CONFIG_SIMULATOR
from octobot_trading.modes import AbstractTradingMode
from tests.test_utils.config import load_test_tentacles_config
from tentacles.Trading import Mode
from tentacles.Evaluator import Strategies
from tentacles.Trading.Mode import DailyTradingMode


DEFAULT_SYMBOL = "ICX/BTC"
DATA_FILE_PATH = "tests/static/"


class AbstractStrategyTest(AbstractBacktestingTest, ABC):
    __metaclass__ = ABCMeta

    def initialize(self, strategy_evaluator_class, trading_mode_class=DailyTradingMode, config=None):
        self.logger = get_logger(self.__class__.__name__)
        self.config = load_test_config() if config is None else config
        # remove fees
        self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES][CONFIG_SIMULATOR_FEES_TAKER] = 0
        self.config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES][CONFIG_SIMULATOR_FEES_MAKER] = 0
        self.strategy_evaluator_class = strategy_evaluator_class
        self.trading_mode_class = trading_mode_class
        self.tentacles_setup_config = load_test_tentacles_config()
        self._update_tentacles_config(strategy_evaluator_class, trading_mode_class)

    def _handle_results(self, independent_backtesting, profitability):
        exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
        for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
            _, run_profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
            actual = round(run_profitability, 3)
            # uncomment this print for building tests
            # print(f"results: rounded run profitability {actual} market profitability: {market_average_profitability}"
            #       f" expected: {profitability} [result: {actual ==  profitability}]")
            assert actual == profitability

    async def _run_backtesting_with_current_config(self, data_file_to_use):
        config_to_use = copy.deepcopy(self.config)
        independent_backtesting = create_independent_backtesting(config_to_use,
                                                                 self.tentacles_setup_config,
                                                                 [data_file_to_use],
                                                                 "")
        await initialize_and_run_independent_backtesting(independent_backtesting, log_errors=False)
        await join_independent_backtesting(independent_backtesting)
        return independent_backtesting

    def _update_tentacles_config(self, strategy_evaluator_class, trading_mode_class):
        default_evaluators = strategy_evaluator_class.get_default_evaluators()
        to_update_config = {}
        tentacles_activation = get_tentacles_activation(self.tentacles_setup_config)
        for tentacle_class_name in tentacles_activation[TENTACLES_EVALUATOR_PATH]:
            if CONFIG_WILDCARD not in default_evaluators and tentacle_class_name in default_evaluators:
                to_update_config[tentacle_class_name] = True
            elif get_class_from_string(tentacle_class_name, StrategyEvaluator, Strategies,
                                       evaluator_parent_inspection) is not None:
                to_update_config[tentacle_class_name] = False
            elif CONFIG_WILDCARD not in default_evaluators:
                to_update_config[tentacle_class_name] = False
        for tentacle_class_name in tentacles_activation[TENTACLES_TRADING_PATH]:
            to_update_config[tentacle_class_name] = False
        # Add required elements if missing
        to_update_config.update({evaluator: True for evaluator in default_evaluators})
        to_update_config[strategy_evaluator_class.get_name()] = True
        to_update_config[trading_mode_class.get_name()] = True
        update_activation_configuration(self.tentacles_setup_config, to_update_config, False, add_missing_elements=True)
