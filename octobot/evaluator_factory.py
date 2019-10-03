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

from octobot_commons.logging.logging_util import get_logger
from octobot_evaluators.api import create_matrix_channels, create_all_type_evaluators, initialize_evaluators
from octobot_trading.exchanges.exchanges import Exchanges
from tools.logger import init_evaluator_chan_logger


class EvaluatorFactory:
    """EvaluatorFactory class:
    - Create evaluators
    """

    def __init__(self, octobot):
        self.octobot = octobot

        # Logger
        self.logger = get_logger(self.__class__.__name__)

        self.symbol_tasks_manager = {}
        self.symbol_evaluator_list = {}
        self.crypto_currency_evaluator_list = {}
        self.dispatchers_list = []
        self.social_eval_tasks = []
        self.real_time_eval_tasks = []

    async def initialize(self):
        await initialize_evaluators(self.octobot.config)
        await create_matrix_channels()

    async def create(self):
        for exchange_configuration in Exchanges.instance().exchanges.values():
            await create_all_type_evaluators(self.octobot.config,
                                             exchange_configuration.exchange_name,
                                             exchange_configuration.symbols,
                                             exchange_configuration.time_frames)
        await init_evaluator_chan_logger()

    # def _check_required_evaluators(self):
    #     if self.symbol_tasks_manager:
    #         etm = next(iter(self.symbol_tasks_manager.values()))
    #         ta_list = etm.get_evaluator().get_ta_eval_list()
    #         if self.octobot.get_relevant_evaluators() != CONFIG_EVALUATORS_WILDCARD:
    #             for required_eval in self.octobot.get_relevant_evaluators():
    #                 required_class = get_class_from_string(required_eval, TAEvaluator, TA, evaluator_parent_inspection)
    #                 if required_class and not self._class_is_in_list(ta_list, required_class):
    #                     self.logger.error(f"Missing technical analysis evaluator {required_class.get_name()} for "
    #                                       f"current strategy. Activate it in OctoBot advanced configuration interface "
    #                                       f"to allow activated strategy(ies) to work properly.")
    #
    # @staticmethod
    # def _class_is_in_list(class_list, required_klass):
    #     return any(required_klass in klass.get_parent_evaluator_classes() for klass in class_list)
