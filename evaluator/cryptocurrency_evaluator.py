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

from tools.logging.logging_util import get_logger

from backtesting import backtesting_enabled
from evaluator.Updaters.social_evaluator_not_tasked_update_task import SocialEvaluatorNotTaskedUpdateTask
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

        if backtesting_enabled(self.config):
            self.social_eval_list = []
            self.social_not_tasked_list = []
        else:
            self.social_eval_list = EvaluatorCreator.create_social_eval(self.config,
                                                                        self.crypto_currency,
                                                                        self.dispatchers_list,
                                                                        relevant_evaluators)

            self.social_not_tasked_list = EvaluatorCreator.create_social_not_tasked_list(self.social_eval_list)

        self.social_evaluator_refresh_task = SocialEvaluatorNotTaskedUpdateTask(self.social_not_tasked_list)

    def add_symbol_evaluator(self, symbol, symbol_evaluator):
        self.symbol_evaluator_list[symbol] = symbol_evaluator

    def _activate_deactivate_strategies(self, strategies, exchange, activate=True):
        try:
            for symbol_evaluator in self.symbol_evaluator_list.values():
                symbol_evaluator.activate_deactivate_strategies(strategies, exchange, activate)
        except Exception as e:
            get_logger(self.__class__.__name__)\
                .error(f"{self.crypto_currency} error in activate_deactivate_strategies(): {e}")

    def deactivate_strategies(self, strategies, exchange):
        self._activate_deactivate_strategies(strategies, exchange, False)

    def activate_strategies(self, strategies, exchange):
        self._activate_deactivate_strategies(strategies, exchange, True)

    def get_social_evaluator_refresh_task(self):
        return self.social_evaluator_refresh_task.start_loop()

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_social_tasked_eval_list(self):
        return [s for s in self.social_eval_list if s.get_is_to_be_started_as_task()]

    def get_dispatchers_list(self):
        return self.dispatchers_list

    def get_social_not_tasked_list(self):
        return self.social_not_tasked_list

    def get_symbol_pairs(self):
        return self.config["crypto_currencies"][self.crypto_currency]["pairs"]

    def get_symbol_evaluator_list(self):
        return self.symbol_evaluator_list

    def get_config(self):
        return self.config
