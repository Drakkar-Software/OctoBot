#  Drakkar-Software OctoBot-Evaluators
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

import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.enums as common_enums
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.evaluators_util as evaluators_util

import octobot_evaluators.api as evaluators_api
import octobot_evaluators.constants as evaluators_constants
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.evaluators.evaluator_factory as evaluator_factory
import octobot_evaluators.matrix as matrix


_EVALUATOR_TYPE = common_enums.UserInputTentacleTypes.EVALUATOR.value


def _make_user_input(
    name,
    input_type,
    def_val,
    value=None,
    title=None,
):
    return user_inputs.UserInput(
        name=name,
        input_type=input_type,
        value=value if value is not None else def_val,
        def_val=def_val,
        tentacle_type=_EVALUATOR_TYPE,
        tentacle_name="FakeEvaluator",
        title=title,
    )


class FakeOHLCVEvaluator(evaluators.TAEvaluator):
    IS_TEST_FAKE_EVALUATOR = True

    @classmethod
    def get_name(cls) -> str:
        return "FakeOHLCVEvaluator"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        if tentacles_setup_config is None:
            import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
            tentacles_setup_config = evaluator_dsl_factory._get_local_tentacles_setup_config()
        return evaluator_factory.create_temporary_evaluator_with_local_config(
            cls, tentacles_setup_config, loaded_config, False
        )

    def init_user_inputs(self, inputs: dict) -> None:
        inputs["threshold"] = _make_user_input(
            "Threshold",
            common_enums.UserInputTypes.FLOAT.value,
            0.5,
            title="Threshold",
        )

    async def ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle,
        inc_in_construction_data,
    ):
        symbol_data = self.get_exchange_symbol_data(exchange, exchange_id, symbol)
        close_candles = symbol_data.get_close_candles(time_frame)
        if close_candles[-1] < close_candles[0]:
            self.eval_note = -1
        else:
            self.eval_note = 1

class FakeEvaluatorWithDslDeps(FakeOHLCVEvaluator):
    @classmethod
    def get_dsl_dependencies(cls, evaluator_config, config, previous_state):
        return [dsl_interpreter.InterpreterDependency()]


class FakeStrategyEvaluator(evaluators.StrategyEvaluator):
    IS_TEST_FAKE_EVALUATOR = True

    @classmethod
    def get_name(cls) -> str:
        return "FakeStrategyEvaluator"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        if tentacles_setup_config is None:
            import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
            tentacles_setup_config = evaluator_dsl_factory._get_local_tentacles_setup_config()
        return evaluator_factory.create_temporary_evaluator_with_local_config(
            cls, tentacles_setup_config, loaded_config, False
        )


FAKE_DUMMY_EVALUATOR_A = "FakeDummyEvaluatorA"
FAKE_DUMMY_EVALUATOR_B = "FakeDummyEvaluatorB"
FAKE_MATRIX_READING_DUMMY_EVALUATORS = (
    FAKE_DUMMY_EVALUATOR_A,
    FAKE_DUMMY_EVALUATOR_B,
)


class FakeMatrixReadingStrategyEvaluator(evaluators.StrategyEvaluator):
    IS_TEST_FAKE_EVALUATOR = True

    @classmethod
    def get_name(cls) -> str:
        return "FakeMatrixReadingStrategyEvaluator"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        if tentacles_setup_config is None:
            import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
            tentacles_setup_config = evaluator_dsl_factory._get_local_tentacles_setup_config()
        return evaluator_factory.create_temporary_evaluator_with_local_config(
            cls, tentacles_setup_config, loaded_config, False
        )

    async def matrix_callback(
        self,
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
        time_frame,
    ):
        evaluations_by_evaluator = matrix.get_evaluations_by_evaluator(
            matrix_id,
            exchange_name,
            evaluators_enums.EvaluatorMatrixTypes.TA.value,
            cryptocurrency,
            symbol,
            time_frame,
        )
        evaluation_count = 0
        total_evaluation = 0
        for dummy_evaluator_name in FAKE_MATRIX_READING_DUMMY_EVALUATORS:
            evaluation = evaluations_by_evaluator.get(dummy_evaluator_name)
            if evaluation is None:
                continue
            evaluation_value = evaluators_api.get_value(evaluation)
            if evaluators_util.check_valid_eval_note(
                evaluation_value,
                eval_type=evaluators_api.get_type(evaluation),
                expected_eval_type=evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
            ):
                total_evaluation += evaluation_value
                evaluation_count += 1
        if evaluation_count > 0:
            self.eval_note = total_evaluation / evaluation_count
            await self.strategy_completed(cryptocurrency, symbol, time_frame)
