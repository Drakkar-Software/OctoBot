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
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.enums as enums


class BlankStrategyEvaluator(evaluators.StrategyEvaluator):

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        super().init_user_inputs(inputs)
        self.UI.user_input(common_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT, common_enums.UserInputTypes.INT,
                        200, inputs, min_val=1,
                        title="Initialization candles count: the number of historical candles to fetch from "
                              "exchanges when OctoBot is starting.")

    def get_full_cycle_evaluator_types(self) -> tuple:
        # returns a tuple as it is faster to create than a list
        return enums.EvaluatorMatrixTypes.TA.value, enums.EvaluatorMatrixTypes.SCRIPTED.value

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
        self.eval_note = eval_note
        await self.strategy_completed(cryptocurrency, symbol, time_frame=time_frame)
