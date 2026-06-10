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
import mock
import pytest

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as common_enums
import octobot_commons.str_util as str_util

import octobot_evaluators.api as evaluator_api
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
import octobot_evaluators.matrix.matrix_manager as matrix_manager

import tests.static.dsl_test_operators as dsl_test_operators
import tests.static.fake_evaluators as fake_evaluators


pytestmark = pytest.mark.asyncio

_FAKE_OHLCV_OPERATOR_NAME = str_util.camel_to_snake(
    fake_evaluators.FakeOHLCVEvaluator.get_name()
)
_FAKE_MATRIX_READING_STRATEGY_OPERATOR_NAME = str_util.camel_to_snake(
    fake_evaluators.FakeMatrixReadingStrategyEvaluator.get_name()
)
_DUMP_CLOSE_CANDLES = [110.0, 105.0, 100.0, 95.0, 90.0]


class _MockSymbolData:
    def __init__(self, close_candles):
        self._close_candles = close_candles

    def get_close_candles(self, _time_frame):
        return self._close_candles


def _mocked_get_exchange_symbol_data(_exchange_name, _exchange_id, _symbol):
    return _MockSymbolData(_DUMP_CLOSE_CANDLES)


def _mock_historical_candles(_symbol_data, _time_frame, limit=1):
    close_candles = _DUMP_CLOSE_CANDLES[-limit:]
    return {
        common_enums.PriceIndexes.IND_PRICE_CLOSE.value: close_candles,
        common_enums.PriceIndexes.IND_PRICE_OPEN.value: close_candles,
        common_enums.PriceIndexes.IND_PRICE_HIGH.value: close_candles,
        common_enums.PriceIndexes.IND_PRICE_LOW.value: close_candles,
        common_enums.PriceIndexes.IND_PRICE_VOL.value: [1.0] * len(close_candles),
        common_enums.PriceIndexes.IND_PRICE_TIME.value: list(range(len(close_candles))),
    }


def _build_evaluator_dsl_statement(
    operator_name: str,
    parameters: dict,
) -> str:
    parameter_parts = [
        f"{parameter_name}={dsl_interpreter.format_parameter_value(parameter_value)}"
        for parameter_name, parameter_value in parameters.items()
    ]
    return f"{operator_name}({', '.join(parameter_parts)})"


def _create_evaluator_interpreter(
    evaluator_class: type,
    exchange_manager,
    matrix_id: str,
    config: dict | None = None,
) -> dsl_interpreter.Interpreter:
    evaluator_operator = evaluator_dsl_factory.create_evaluator_operator(
        evaluator_class,
        exchange_manager,
        config or {},
        matrix_id,
    )
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + [dsl_test_operators.ListOperator, evaluator_operator]
    )


class TestEvaluatorDslInterpreterFakeOHLCVEvaluator:
    async def test_interpreter_returns_eval_note_from_keyword(self, matrix_id):
        await evaluator_api.create_evaluator_channels(matrix_id)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binanceus"
        try:
            with (
                mock.patch.object(
                    fake_evaluators.FakeOHLCVEvaluator,
                    "get_exchange_symbol_data",
                    new=staticmethod(_mocked_get_exchange_symbol_data),
                ),
                mock.patch(
                    "octobot_trading.api.are_symbol_candles_initialized",
                    return_value=True,
                ),
                mock.patch(
                    "octobot_trading.api.get_exchange_id_from_matrix_id",
                    return_value="exchange_id",
                ),
                mock.patch(
                    "octobot_trading.api.get_symbol_historical_candles",
                    side_effect=_mock_historical_candles,
                ),
                mock.patch(
                    "octobot_trading.api.get_candle_as_list",
                    return_value=[0, 0, 0, 0, _DUMP_CLOSE_CANDLES[-1], 0],
                ),
            ):
                interpreter = _create_evaluator_interpreter(
                    fake_evaluators.FakeOHLCVEvaluator,
                    exchange_manager,
                    matrix_id,
                )
                dsl_statement = _build_evaluator_dsl_statement(
                    _FAKE_OHLCV_OPERATOR_NAME,
                    {
                        "symbols": ["BTC/USDC"],
                        "time_frames": ["2h"],
                    },
                )
                result = await interpreter.interprete(dsl_statement)
            assert len(result) == 1
            evaluator_result = result[0]
            assert evaluator_result["eval_note"] == -1
            assert evaluator_result["evaluator_name"] == fake_evaluators.FakeOHLCVEvaluator.get_name()
            assert evaluator_result["symbol"] == "BTC/USDC"
            assert evaluator_result["time_frame"] == "2h"
            tentacle_path = matrix_manager.get_matrix_default_value_path(
                fake_evaluators.FakeOHLCVEvaluator.get_name(),
                evaluators_enums.EvaluatorMatrixTypes.TA.value,
                exchange_name="binanceus",
                cryptocurrency="BTC",
                symbol="BTC/USDC",
                time_frame="2h",
            )
            assert matrix_manager.get_tentacle_value(matrix_id, tentacle_path) == -1
        finally:
            evaluator_api.del_evaluator_channels(matrix_id)


class TestEvaluatorDslInterpreterFakeMatrixReadingStrategyEvaluator:
    async def test_strategy_reads_dummy_evaluator_values_from_matrix(self, matrix_id):
        await evaluator_api.create_evaluator_channels(matrix_id)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binanceus"
        try:
            dynamic_dependencies = [
                {
                    "operator_name": "dummy_evaluator_a",
                    "result": {
                        "eval_note": 1,
                        "symbol": "BTC/USDC",
                        "time_frame": "1h",
                        "evaluator_name": fake_evaluators.FAKE_DUMMY_EVALUATOR_A,
                        "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
                        "cryptocurrency": "BTC",
                    },
                },
                {
                    "operator_name": "dummy_evaluator_b",
                    "result": {
                        "eval_note": 0.5,
                        "symbol": "BTC/USDC",
                        "time_frame": "1h",
                        "evaluator_name": fake_evaluators.FAKE_DUMMY_EVALUATOR_B,
                        "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
                        "cryptocurrency": "BTC",
                    },
                },
            ]

            async def _create_strategy_instance(*_args, **_kwargs):
                strategy_instance = fake_evaluators.FakeMatrixReadingStrategyEvaluator(
                    evaluator_dsl_factory._get_local_tentacles_setup_config()
                )
                strategy_instance.matrix_id = matrix_id
                strategy_instance.evaluator_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES
                strategy_instance.strategy_time_frames = [common_enums.TimeFrames.ONE_HOUR]
                return strategy_instance

            interpreter = _create_evaluator_interpreter(
                fake_evaluators.FakeMatrixReadingStrategyEvaluator,
                exchange_manager,
                matrix_id,
            )
            dsl_statement = _build_evaluator_dsl_statement(
                _FAKE_MATRIX_READING_STRATEGY_OPERATOR_NAME,
                {
                    "time_frames": ["1h"],
                    "_dynamic_dependencies": dynamic_dependencies,
                },
            )
            with mock.patch.object(
                evaluator_dsl_factory.evaluator_factory,
                "create_dsl_evaluator",
                mock.AsyncMock(side_effect=_create_strategy_instance),
            ):
                result = await interpreter.interprete(dsl_statement)
            assert len(result) == 1
            evaluator_result = result[0]
            assert evaluator_result["eval_note"] == 0.75
            assert evaluator_result["evaluator_name"] == (
                fake_evaluators.FakeMatrixReadingStrategyEvaluator.get_name()
            )
            assert evaluator_result["symbol"] == "BTC/USDC"
            assert evaluator_result["time_frame"] == "1h"
            dummy_a_path = matrix_manager.get_matrix_default_value_path(
                fake_evaluators.FAKE_DUMMY_EVALUATOR_A,
                evaluators_enums.EvaluatorMatrixTypes.TA.value,
                exchange_name="binanceus",
                cryptocurrency="BTC",
                symbol="BTC/USDC",
                time_frame="1h",
            )
            assert matrix_manager.get_tentacle_value(matrix_id, dummy_a_path) == 1
        finally:
            evaluator_api.del_evaluator_channels(matrix_id)
