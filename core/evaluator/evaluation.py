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
from config import CONFIG_EVALUATORS_WILDCARD, CONFIG_SAVE_EVALUATION, EvaluatorMatrixTypes, START_PENDING_EVAL_NOTE
from core.consumer import Consumer
from evaluator.evaluator import Evaluator
from tools import get_logger
from tools.exporter import MatrixExporter


class EvaluationConsumer(Consumer):
    TRIGGER_TAG = "TAG"
    REFRESHED_TIMES = "REFRESHED_TIMES"

    def __init__(self, config,
                 ohlcv_consumer,
                 time_frame,
                 symbol_evaluator,
                 exchange,
                 trading_mode,
                 real_time_ta_eval_list,
                 relevant_evaluators=None):
        super().__init__()

        if relevant_evaluators is None:
            relevant_evaluators = CONFIG_EVALUATORS_WILDCARD

        self.config = config
        self.ohlcv_consumer = ohlcv_consumer
        self.exchange = exchange
        self.trading_mode = trading_mode
        self.symbol = symbol_evaluator.symbol
        self.time_frame = time_frame
        self.symbol_evaluator = symbol_evaluator
        self.should_refresh_matrix_evaluation_types = True
        self.relevant_evaluators = relevant_evaluators
        self.real_time_ta_eval_list = real_time_ta_eval_list

        self.evaluator = Evaluator()

        self.should_save_evaluations = CONFIG_SAVE_EVALUATION in self.config and self.config[CONFIG_SAVE_EVALUATION]

        # notify symbol evaluator
        self.symbol_evaluator.add_evaluation_consumer(self.exchange, self.time_frame, self.trading_mode, self)

        self.matrix = self.symbol_evaluator.get_matrix(self.exchange)

        if self.should_save_evaluations:
            self.matrix_exporter = MatrixExporter(self.matrix, self.symbol)

        self.task_name = f"Evaluator TASK MANAGER - {self.symbol} - {self.exchange.get_name()} - {self.time_frame}"
        self.logger = get_logger(self.task_name)

        # Create Evaluator
        self.evaluator.config = self.config
        self.evaluator.symbol = self.symbol
        self.evaluator.time_frame = self.time_frame
        self.evaluator.exchange = self.exchange
        self.evaluator.symbol_evaluator = self.symbol_evaluator

        # Add tasked evaluators that can notify the current task
        self.evaluator.set_social_eval(self.symbol_evaluator.crypto_currency_evaluator.social_eval_list, self)
        self.evaluator.set_real_time_eval(self.real_time_ta_eval_list, self)

        # Create static evaluators
        self.evaluator.set_ta_eval_list(self.evaluator.creator.create_ta_eval_list(self.evaluator,
                                                                                   self.relevant_evaluators), self)

    async def consume(self):
        while not self.should_stop:
            trigger_data = (await self.queue.get())

            trigger_tag = trigger_data[self.TRIGGER_TAG]
            trigger_refreshed_times = trigger_data[self.REFRESHED_TIMES]

            if self._should_consider_notification(trigger_tag, trigger_refreshed_times):
                self.logger.debug(f"** Triggered by {trigger_tag} **")
                # if force_TA_refresh: TODO
                #     await self.global_price_updater.force_refresh_data(self.time_frame, self.symbol)
                await self.perform(trigger_tag)

    def _should_consider_notification(self, trigger_tag, trigger_refreshed_times):
        if trigger_refreshed_times > 0:
            # if notification from interruption (real_time or social evaluator,
            # ensure first that everything is initialized properly
            return_val = self.symbol_evaluator.are_all_timeframes_initialized(self.exchange)
        # elif not self.has_symbol_in_update_list():
        #     return True TODO
        else:
            return_val = False
        if not return_val:
            self.logger.debug(f"Notification by {trigger_tag} ignored")
        return return_val

    async def perform(self, ignored_evaluator=None, finalize=False):
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

        self._refresh_matrix_type(self.evaluator.ta_eval_list,
                                  EvaluatorMatrixTypes.TA,
                                  refresh_matrix_evaluation_types=refresh_matrix_evaluation_types)

        self._refresh_matrix_type(self.evaluator.social_eval_list,
                                  EvaluatorMatrixTypes.SOCIAL,
                                  refresh_matrix_evaluation_types=refresh_matrix_evaluation_types)

        self._refresh_matrix_type(self.evaluator.real_time_eval_list,
                                  EvaluatorMatrixTypes.REAL_TIME,
                                  refresh_matrix_evaluation_types=refresh_matrix_evaluation_types)

    def _refresh_matrix_type(self, evaluator_list, evaluator_type, refresh_matrix_evaluation_types=False):
        for evaluator in evaluator_list:
            if evaluator.get_is_active():
                evaluator.ensure_eval_note_is_not_expired()
                self.matrix.set_eval(evaluator_type, evaluator.get_name(), evaluator.get_eval_note())
            else:
                self.matrix.set_eval(evaluator_type, evaluator.get_name(), START_PENDING_EVAL_NOTE)

            if refresh_matrix_evaluation_types:
                self.matrix.set_evaluator_eval_type(evaluator.get_name(), evaluator.get_eval_type())

    def _save_evaluations_if_necessary(self):
        if self.should_save_evaluations and self.symbol_evaluator.are_all_timeframes_initialized(self.exchange):
            self.matrix_exporter.save()

    def get_refreshed_times(self):
        return self.ohlcv_consumer.get_refreshed_times(self.time_frame, self.symbol)

    def has_symbol_in_update_list(self):
        return self.ohlcv_consumer.has_this_symbol_in_update_list(self.symbol)

    @staticmethod
    def create_feed(tag=None, refreshed_times=None):
        return {
            EvaluationConsumer.TRIGGER_TAG: tag,
            EvaluationConsumer.REFRESHED_TIMES: refreshed_times
        }
