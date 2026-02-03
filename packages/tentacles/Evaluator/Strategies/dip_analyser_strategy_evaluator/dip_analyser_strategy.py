#  Drakkar-Software OctoBot-Tentacles
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
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_evaluators.api.matrix as evaluators_api
import octobot_evaluators.evaluators.channel as evaluator_channel
import octobot_evaluators.constants as evaluator_constants
import octobot_evaluators.matrix as matrix
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.evaluators as evaluators
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.api as trading_api
import tentacles.Evaluator.TA as TA


class DipAnalyserStrategyEvaluator(evaluators.StrategyEvaluator):
    REVERSAL_CONFIRMATION_CLASS_NAME = TA.KlingerOscillatorReversalConfirmationMomentumEvaluator.get_name()
    REVERSAL_WEIGHT_CLASS_NAME = TA.RSIWeightMomentumEvaluator.get_name()

    @staticmethod
    def get_eval_type():
        return typing.Dict[str, int]

    def __init__(self, tentacles_setup_config):
        super().__init__(tentacles_setup_config)
        self.evaluation_time_frame = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.evaluation_time_frame = self.evaluation_time_frame or commons_enums.TimeFrames(
            self.UI.user_input(
                evaluator_constants.STRATEGIES_REQUIRED_TIME_FRAME,
                commons_enums.UserInputTypes.MULTIPLE_OPTIONS,
                [commons_enums.TimeFrames.ONE_HOUR.value],
                inputs, options=[tf.value for tf in commons_enums.TimeFrames],
                title="Analysed time frame: only the first one will be considered for DipAnalyserStrategyEvaluator."
            )[0]
        ).value

    async def matrix_callback(self,
                              matrix_id,
                              evaluator_name,
                              evaluator_type,
                              eval_note,
                              eval_note_type,
                              eval_note_description,
                              eval_note_metadata,
                              exchange_name,
                              cryptocurrency,
                              symbol,
                              time_frame):
        if evaluator_type == evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value:
            # trigger re-evaluation
            exchange_id = trading_api.get_exchange_id_from_matrix_id(exchange_name, matrix_id)
            await evaluator_channel.trigger_technical_evaluators_re_evaluation_with_updated_data(matrix_id,
                                                                                                 evaluator_name,
                                                                                                 evaluator_type,
                                                                                                 exchange_name,
                                                                                                 cryptocurrency,
                                                                                                 symbol,
                                                                                                 exchange_id,
                                                                                                 self.strategy_time_frames)
            # do not continue this evaluation
            return
        elif evaluator_type == evaluators_enums.EvaluatorMatrixTypes.TA.value:
            self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
            TA_evaluations = matrix.get_evaluations_by_evaluator(matrix_id,
                                                                 exchange_name,
                                                                 evaluators_enums.EvaluatorMatrixTypes.TA.value,
                                                                 cryptocurrency,
                                                                 symbol,
                                                                 self.evaluation_time_frame,
                                                                 allowed_values=[
                                                                     commons_constants.START_PENDING_EVAL_NOTE])

            try:
                if evaluators_api.get_value(TA_evaluations[self.REVERSAL_CONFIRMATION_CLASS_NAME]):
                    self.eval_note = evaluators_api.get_value(TA_evaluations[self.REVERSAL_WEIGHT_CLASS_NAME])
                await self.strategy_completed(cryptocurrency, symbol)
            except KeyError as e:
                self.logger.error(f"Missing required evaluator: {e}")
