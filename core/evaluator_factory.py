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
from backtesting import backtesting_enabled
from config import CONFIG_CRYPTO_CURRENCIES, CONFIG_EVALUATORS_WILDCARD
from evaluator import TA
from evaluator.TA import TAEvaluator
from evaluator.Updaters.global_price_updater import GlobalPriceUpdater
from evaluator.cryptocurrency_evaluator import CryptocurrencyEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.evaluator_task_manager import EvaluatorTaskManager
from evaluator.symbol_evaluator import SymbolEvaluator
from services.Dispatchers.dispatcher_creator import DispatcherCreator
from tentacles_management.class_inspector import evaluator_parent_inspection, get_class_from_string
from tools.logging.logging_util import get_logger


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

    def create(self):
        self.create_dispatchers()
        self.evaluation_tasks_creation()

    def create_dispatchers(self):
        self.dispatchers_list = DispatcherCreator.create_dispatchers(self.octobot.get_config(),
                                                                     self.octobot.get_async_loop())

    def evaluation_tasks_creation(self):
        self.logger.info("Evaluation threads creation...")

        # create Social and TA evaluators
        for crypto_currency in self.octobot.get_config()[CONFIG_CRYPTO_CURRENCIES]:
            self._create_crypto_currency_evaluator_tasks(crypto_currency)

        self._check_required_evaluators()

    def _create_crypto_currency_evaluator_tasks(self, crypto_currency):
        crypto_currency_evaluator = self._create_crypto_currency_evaluator(crypto_currency)
        self.social_eval_tasks += crypto_currency_evaluator.get_social_tasked_eval_list()

        # create symbol evaluators
        for exchange in self.octobot.exchange_factory.exchanges_list.values():
            if exchange.get_exchange_manager().enabled():
                self._create_symbol_evaluators(exchange, crypto_currency)

    def _create_crypto_currency_evaluator(self, crypto_currency) -> CryptocurrencyEvaluator:
        crypto_currency_evaluator = CryptocurrencyEvaluator(self.octobot.get_config(), crypto_currency,
                                                            self.dispatchers_list,
                                                            self.octobot.get_relevant_evaluators())
        self.crypto_currency_evaluator_list[crypto_currency] = crypto_currency_evaluator
        return crypto_currency_evaluator

    def _create_symbol_evaluators(self, exchange, crypto_currency):
        # create TA evaluators
        for symbol in exchange.get_exchange_manager().get_traded_pairs(cryptocurrency=crypto_currency):
            if symbol in self.symbol_evaluator_list:
                symbol_evaluator = self.symbol_evaluator_list[symbol]
            else:
                symbol_evaluator = self._create_symbol_evaluator(symbol,
                                                                 self.crypto_currency_evaluator_list[crypto_currency])

            self._create_symbol_threads_managers(exchange,
                                                 symbol_evaluator,
                                                 self._get_global_price_updater_from_exchange_name(exchange))

    def _create_symbol_evaluator(self, symbol, crypto_currency_evaluator) -> SymbolEvaluator:
        symbol_evaluator = SymbolEvaluator(self.octobot.get_config(), symbol, crypto_currency_evaluator)
        symbol_evaluator.set_traders(self.octobot.get_exchange_traders())
        symbol_evaluator.set_trader_simulators(self.octobot.get_exchange_trader_simulators())
        crypto_currency_evaluator.add_symbol_evaluator(symbol, symbol_evaluator)
        self.symbol_evaluator_list[symbol] = symbol_evaluator
        return symbol_evaluator

    def _get_global_price_updater_from_exchange_name(self, exchange) -> GlobalPriceUpdater:
        return self.octobot.get_global_updaters_by_exchange()[exchange.get_name()]

    def _create_symbol_threads_managers(self, exchange, symbol_evaluator, global_price_updater):
        real_time_ta_eval_list = self._create_real_time_ta_list(exchange, symbol_evaluator)

        if self.octobot.get_time_frames():
            self._create_evaluator_task_managers_with_time_frame(exchange,
                                                                 symbol_evaluator,
                                                                 global_price_updater,
                                                                 real_time_ta_eval_list)
        else:
            # without time frame
            self.symbol_tasks_manager[None] = \
                self._create_evaluator_task_manager(time_frame=None,
                                                    global_price_updater=global_price_updater,
                                                    symbol_evaluator=symbol_evaluator,
                                                    exchange=exchange,
                                                    real_time_ta_eval_list=real_time_ta_eval_list)

    def _create_evaluator_task_managers_with_time_frame(self,
                                                        exchange,
                                                        symbol_evaluator,
                                                        global_price_updater,
                                                        real_time_ta_eval_list):
        for time_frame in self.octobot.get_time_frames():
            if self._is_time_frame_exists_in_exchange(exchange, symbol_evaluator, time_frame):
                self.symbol_tasks_manager[time_frame] = \
                    self._create_evaluator_task_manager(time_frame=time_frame,
                                                        global_price_updater=global_price_updater,
                                                        symbol_evaluator=symbol_evaluator,
                                                        exchange=exchange,
                                                        real_time_ta_eval_list=real_time_ta_eval_list)
            else:
                self.logger.error(f"{exchange.get_name()} exchange is not supporting the required time frame: "
                                  f"'{time_frame.value}' for {symbol_evaluator.get_symbol()}.")

    @staticmethod
    def _is_time_frame_exists_in_exchange(exchange, symbol_evaluator, time_frame):
        return exchange.get_exchange_manager().time_frame_exists(time_frame.value, symbol_evaluator.get_symbol())

    def _create_real_time_ta_list(self, exchange, symbol_evaluator):
        real_time_ta_eval_list = []
        if not backtesting_enabled(self.octobot.get_config()):
            real_time_ta_eval_list = self._create_real_time_ta_evaluators(exchange, symbol_evaluator)
            self.real_time_eval_tasks += real_time_ta_eval_list

        return real_time_ta_eval_list

    def _create_real_time_ta_evaluators(self, exchange, symbol_evaluator):
        return EvaluatorCreator.create_real_time_ta_evals(self.octobot.get_config(),
                                                          exchange,
                                                          symbol_evaluator.get_symbol(),
                                                          self.octobot.get_relevant_evaluators(),
                                                          self.dispatchers_list)

    def _create_evaluator_task_manager(self,
                                       time_frame,
                                       global_price_updater,
                                       symbol_evaluator,
                                       exchange,
                                       real_time_ta_eval_list) -> EvaluatorTaskManager:

        return EvaluatorTaskManager(self.octobot.get_config(),
                                    time_frame,
                                    global_price_updater,
                                    symbol_evaluator,
                                    exchange,
                                    self.octobot.get_exchange_trading_modes()[exchange.get_name()],
                                    real_time_ta_eval_list,
                                    self.octobot.get_async_loop(),
                                    self.octobot.get_relevant_evaluators())

    def _check_required_evaluators(self):
        if self.symbol_tasks_manager:
            etm = next(iter(self.symbol_tasks_manager.values()))
            ta_list = etm.get_evaluator().get_ta_eval_list()
            if self.octobot.get_relevant_evaluators() != CONFIG_EVALUATORS_WILDCARD:
                for required_eval in self.octobot.get_relevant_evaluators():
                    required_class = get_class_from_string(required_eval, TAEvaluator, TA, evaluator_parent_inspection)
                    if required_class and not self._class_is_in_list(ta_list, required_class):
                        self.logger.error(f"Missing technical analysis evaluator {required_class.get_name()} for "
                                          f"current strategy. Activate it in OctoBot advanced configuration interface "
                                          f"to allow activated strategy(ies) to work properly.")

    @staticmethod
    def _class_is_in_list(class_list, required_klass):
        return any(required_klass in klass.get_parent_evaluator_classes() for klass in class_list)
