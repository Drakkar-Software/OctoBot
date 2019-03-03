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

from config import CONFIG_EVALUATORS_WILDCARD, EvaluatorMatrixTypes, START_PENDING_EVAL_NOTE, \
    CONFIG_SAVE_EVALUATION
from evaluator.evaluator import Evaluator
from tools.exporter import MatrixExporter

"""
This class represent the last level of evaluator management by :
- Providing a link between evaluators and symbol evaluation matrix (through notifications)
- Refreshing matrix with evaluators eval_note
"""


class EvaluatorTaskManager:
    def __init__(self, config,
                 time_frame,
                 global_price_updater,
                 symbol_evaluator,
                 exchange,
                 trading_mode,
                 real_time_ta_eval_list,
                 main_loop,
                 relevant_evaluators=None):

        if relevant_evaluators is None:
            relevant_evaluators = CONFIG_EVALUATORS_WILDCARD
        self.config = config
        self.exchange = exchange
        self.trading_mode = trading_mode
        self.symbol = symbol_evaluator.get_symbol()
        self.time_frame = time_frame
        self.global_price_updater = global_price_updater
        self.symbol_evaluator = symbol_evaluator
        self.main_loop = main_loop
        self.should_refresh_matrix_evaluation_types = True

        self.should_save_evaluations = CONFIG_SAVE_EVALUATION in self.config and self.config[CONFIG_SAVE_EVALUATION]

        # notify symbol evaluator
        self.symbol_evaluator.add_evaluator_task_manager(self.exchange, self.time_frame, self.trading_mode, self)

        self.matrix = self.symbol_evaluator.get_matrix(self.exchange)
        self.matrix_exporter = MatrixExporter(self.matrix, self.symbol)

        self.task_name = f"Evaluator TASK MANAGER - {self.symbol} - {self.exchange.get_name()} - {self.time_frame}"
        self.logger = get_logger(self.task_name)

        # Create Evaluator
        self.evaluator = Evaluator()
        self.evaluator.set_config(self.config)
        self.evaluator.set_symbol(self.symbol)
        self.evaluator.set_time_frame(self.time_frame)
        self.evaluator.set_exchange(self.exchange)
        self.evaluator.set_symbol_evaluator(self.symbol_evaluator)

        # Add tasked evaluators that can notify the current task
        self.evaluator.set_social_eval(self.symbol_evaluator.get_crypto_currency_evaluator().get_social_eval_list(),
                                       self)
        self.evaluator.set_real_time_eval(real_time_ta_eval_list, self)

        # Create static evaluators
        self.evaluator.set_ta_eval_list(self.evaluator.get_creator().create_ta_eval_list(self.evaluator,
                                                                                         relevant_evaluators), self)

        # Register in refreshing task
        self.global_price_updater.register_evaluator_task_manager(self.time_frame, self)

    # handle notifications from evaluators, when notified refresh symbol evaluation matrix
    async def notify(self, notifier_name, force_TA_refresh=False, finalize=False, interruption=False):
        if self._should_consider_notification(notifier_name, interruption=interruption):
            self.logger.debug(f"** Notified by {notifier_name} **")
            if force_TA_refresh:
                await self.global_price_updater.force_refresh_data(self.time_frame, self.symbol)
            await self._refresh_eval(notifier_name, finalize=finalize)

    def _should_consider_notification(self, notifier_name, interruption=False):
        if self.get_refreshed_times() > 0:
            if interruption:
                # if notification from interruption (real_time or social evaluator,
                # ensure first that everything is initialized properly
                return_val = self.symbol_evaluator.are_all_timeframes_initialized(self.exchange)
            else:
                return True
        elif not self.has_symbol_in_update_list():
            return True
        else:
            return_val = False
        if not return_val:
            self.logger.debug(f"Notification by {notifier_name} ignored")
        return return_val

    async def _refresh_eval(self, ignored_evaluator=None, finalize=False):
        # update eval
        await self.evaluator.update_ta_eval(ignored_evaluator)

        # update matrix
        self.refresh_matrix(refresh_matrix_evaluation_types=self.should_refresh_matrix_evaluation_types)

        # update strategies matrix
        await self.symbol_evaluator.update_strategies_eval(
            self.matrix, self.exchange, ignored_evaluator,
            refresh_matrix_evaluation_types=self.should_refresh_matrix_evaluation_types)

        self.should_refresh_matrix_evaluation_types = False

        self.logger.debug(f"MATRIX : {self.matrix.get_matrix()}")

        if finalize:
            # calculate the final result
            await self.symbol_evaluator.finalize(self.exchange)

        # save evaluations if option is activated
        self._save_evaluations_if_necessary()

    def refresh_matrix(self, refresh_matrix_evaluation_types=False):
        self.matrix = self.symbol_evaluator.get_matrix(self.exchange)

        for ta_eval in self.evaluator.get_ta_eval_list():
            if ta_eval.get_is_active():
                ta_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.get_name(),
                                     ta_eval.get_eval_note(), self.time_frame)
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.TA, ta_eval.get_name(),
                                     START_PENDING_EVAL_NOTE, self.time_frame)
            if refresh_matrix_evaluation_types:
                self.matrix.set_evaluator_eval_type(ta_eval.get_name(), ta_eval.get_eval_type())

        for social_eval in self.evaluator.get_social_eval_list():
            if social_eval.get_is_active():
                social_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.get_name(),
                                     social_eval.get_eval_note(), None)
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.SOCIAL, social_eval.get_name(),
                                     START_PENDING_EVAL_NOTE)
            if refresh_matrix_evaluation_types:
                self.matrix.set_evaluator_eval_type(social_eval.get_name(), social_eval.get_eval_type())

        for real_time_eval in self.evaluator.get_real_time_eval_list():
            if real_time_eval.get_is_active():
                real_time_eval.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(EvaluatorMatrixTypes.REAL_TIME, real_time_eval.get_name(),
                                     real_time_eval.get_eval_note())
            else:
                self.matrix.set_eval(EvaluatorMatrixTypes.REAL_TIME, real_time_eval.get_name(),
                                     START_PENDING_EVAL_NOTE)
            if refresh_matrix_evaluation_types:
                self.matrix.set_evaluator_eval_type(real_time_eval.get_name(), real_time_eval.get_eval_type())

    def _save_evaluations_if_necessary(self):
        if self.should_save_evaluations and self.symbol_evaluator.are_all_timeframes_initialized(self.exchange):
            self.matrix_exporter.save()

    def get_refreshed_times(self):
        return self.global_price_updater.get_refreshed_times(self.time_frame, self.symbol)

    def has_symbol_in_update_list(self):
        return self.global_price_updater.has_this_symbol_in_update_list(self.symbol)

    def get_evaluator(self):
        return self.evaluator

    def get_global_price_updater(self):
        return self.global_price_updater

    def get_exchange(self):
        return self.exchange

    def get_symbol_evaluator(self):
        return self.symbol_evaluator

    def get_symbol(self):
        return self.symbol
