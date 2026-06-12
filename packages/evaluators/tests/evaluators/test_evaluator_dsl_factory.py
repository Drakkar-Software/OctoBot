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

import octobot_commons.databases as commons_databases
import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as common_enums
import octobot_commons.errors as commons_errors
import octobot_commons.str_util as str_util

import octobot_evaluators.api as evaluator_api
import octobot_evaluators.constants as evaluators_constants
import octobot_evaluators.enums as evaluators_enums
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.evaluators.evaluator_dsl_factory as evaluator_dsl_factory
import octobot_evaluators.matrix.matrix_manager as matrix_manager
import octobot_trading.dsl as trading_dsl

import tests.static.fake_evaluators as fake_evaluators


_EVALUATOR_TYPE = common_enums.UserInputTentacleTypes.EVALUATOR.value


def _make_user_input(name, input_type, def_val, value=None, title=None):
    return user_inputs.UserInput(
        name=name,
        input_type=input_type,
        value=value if value is not None else def_val,
        def_val=def_val,
        tentacle_type=_EVALUATOR_TYPE,
        tentacle_name="FakeEvaluator",
        title=title,
    )


class FakeEvaluatorAlpha:
    @classmethod
    def get_name(cls) -> str:
        return "FakeEvaluatorAlpha"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        instance = mock.Mock()
        instance.init_user_inputs = lambda inputs: inputs.update({
            "top_int": _make_user_input(
                "Top Level Int",
                common_enums.UserInputTypes.INT.value,
                0,
                title="Integer setting",
            ),
        })
        instance.get_name = mock.Mock(return_value=cls.get_name())
        instance.eval_note = 1
        return instance

    @classmethod
    def get_dsl_dependencies(cls, evaluator_config, config, previous_state):
        return []


class FakeEvaluatorWithDslDeps(FakeEvaluatorAlpha):
    @classmethod
    def get_dsl_dependencies(cls, evaluator_config, config, previous_state):
        return [dsl_interpreter.InterpreterDependency()]


def _operator_with_exchange_manager(matrix_id="matrix-1"):
    exchange_manager = mock.Mock()
    exchange_manager.exchange_name = "binanceus"
    OpCls = evaluator_dsl_factory.create_evaluator_operator(
        FakeEvaluatorAlpha,
        exchange_manager,
        {},
        matrix_id,
    )
    return OpCls(), exchange_manager


class TestEvaluatorResult:
    def test_eval_note_type_as_str_serializes_type_objects(self):
        assert evaluator_dsl_factory.evaluator_result.eval_note_type_as_str(float) == "float"
        assert evaluator_dsl_factory.evaluator_result.eval_note_type_as_str("float") == "float"
        assert evaluator_dsl_factory.evaluator_result.eval_note_type_as_str(None) is None

    def test_to_dict_from_dict_round_trip(self):
        evaluator_result = evaluator_dsl_factory.EvaluatorResult(
            symbol="BTC/USDC",
            time_frame="2h",
            evaluator_name="FakeOHLCVEvaluator",
            evaluator_type=evaluators_enums.EvaluatorMatrixTypes.TA.value,
            cryptocurrency="BTC",
            eval_note=-1,
            eval_note_type=evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE,
            eval_time=1234.0,
            eval_note_description="desc",
            eval_note_metadata={"k": "v"},
        )
        parsed_result = evaluator_dsl_factory.EvaluatorResult.from_dict(
            evaluator_result.to_dict(include_default_values=False)
        )
        assert parsed_result.eval_note == evaluator_result.eval_note
        assert parsed_result.eval_note_type == evaluator_result.eval_note_type
        assert parsed_result.eval_time == evaluator_result.eval_time
        assert parsed_result.eval_note_description == evaluator_result.eval_note_description
        assert parsed_result.eval_note_metadata == evaluator_result.eval_note_metadata
        assert parsed_result.symbol == evaluator_result.symbol
        assert parsed_result.evaluator_name == evaluator_result.evaluator_name

    def test_from_dict_applies_defaults_for_missing_eval_fields(self):
        parsed_result = evaluator_dsl_factory.EvaluatorResult.from_dict({
            "symbol": "BTC/USDC",
            "time_frame": "2h",
            "evaluator_name": "FakeOHLCVEvaluator",
            "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
            "cryptocurrency": "BTC",
            "eval_note": -1,
        })
        assert parsed_result.eval_note == -1
        assert parsed_result.eval_note_type is None
        assert parsed_result.eval_time == 0
        assert parsed_result.eval_note_description is None
        assert parsed_result.eval_note_metadata is None


class TestEnsureDslBotStorageRegistered:
    @pytest.mark.asyncio
    async def test_registers_dsl_bot_with_disabled_storage(self):
        provider = commons_databases.RunDatabasesProvider.instance()
        if provider.has_bot_id(evaluator_dsl_factory.DSL_BOT_ID):
            provider.remove_bot_id(evaluator_dsl_factory.DSL_BOT_ID)
        await evaluator_dsl_factory._ensure_dsl_bot_storage_registered()
        assert provider.has_bot_id(evaluator_dsl_factory.DSL_BOT_ID)
        assert provider.is_storage_enabled(evaluator_dsl_factory.DSL_BOT_ID) is False


class TestCreateEvaluatorOperator:
    def test_operator_exposes_dynamic_dependencies_parameter(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeOHLCVEvaluator,
            None,
            {},
            None,
        )
        parameter_names = {parameter.name for parameter in OpCls.get_parameters()}
        assert "_dynamic_dependencies" in parameter_names
        assert "double_moving_average_trend_evaluator_result" not in parameter_names

    def test_operator_name_from_evaluator_class(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeOHLCVEvaluator,
            None,
            {},
            None,
        )
        assert OpCls.get_name() == str_util.camel_to_snake(
            fake_evaluators.FakeOHLCVEvaluator.get_name()
        )

    def test_parameters_include_user_inputs_and_meta(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeOHLCVEvaluator,
            None,
            {},
            None,
        )
        parameter_names = {parameter.name for parameter in OpCls.get_parameters()}
        assert "Threshold" in parameter_names
        parameters_by_name = {
            parameter.name: parameter for parameter in OpCls.get_parameters()
        }
        assert evaluator_dsl_factory.SYMBOLS_PARAM in parameters_by_name
        assert evaluator_dsl_factory.TIME_FRAMES_PARAM in parameters_by_name
        assert parameters_by_name[evaluator_dsl_factory.SYMBOLS_PARAM].type is list
        assert parameters_by_name[evaluator_dsl_factory.TIME_FRAMES_PARAM].type is list
        assert evaluator_dsl_factory.INCLUDE_IN_CONSTRUCTION_CANDLE_PARAM in parameter_names

    def test_strategy_operator_meta_parameters_only_time_frames(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeStrategyEvaluator,
            None,
            {},
            None,
        )
        meta_parameters_by_name = {
            parameter.name: parameter
            for parameter in OpCls.get_evaluator_meta_parameters()
        }
        assert set(meta_parameters_by_name) == {evaluator_dsl_factory.TIME_FRAMES_PARAM}
        assert meta_parameters_by_name[evaluator_dsl_factory.TIME_FRAMES_PARAM].type is list


class TestGetDependencies:
    def test_merges_super_and_evaluator_dependencies(self):
        base_dependency = dsl_interpreter.InterpreterDependency()
        local_dependency = dsl_interpreter.InterpreterDependency()
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            FakeEvaluatorWithDslDeps,
            None,
            {"global": True},
            None,
        )
        operator = OpCls()
        with mock.patch(
            "octobot_commons.dsl_interpreter.operator.Operator.get_dependencies",
            mock.Mock(return_value=[base_dependency]),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                mock.Mock(return_value={"param": 1}),
            ):
                with mock.patch.object(
                    FakeEvaluatorWithDslDeps,
                    "get_dsl_dependencies",
                    mock.Mock(return_value=[local_dependency]),
                ) as get_dsl_dependencies_mock:
                    dependencies = operator.get_dependencies()
                    get_dsl_dependencies_mock.assert_called_once_with({"param": 1}, {"global": True}, None)
        assert dependencies == [base_dependency, local_dependency]

    def test_includes_symbol_dependencies_from_dynamic_dependencies_for_ta_evaluator(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            FakeEvaluatorAlpha,
            None,
            {},
            None,
        )
        operator = OpCls()
        with mock.patch(
            "octobot_commons.dsl_interpreter.operator.Operator.get_dependencies",
            mock.Mock(return_value=[]),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                mock.Mock(
                    return_value={
                        evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDT"],
                        evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                        dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY: [
                            {
                                "operator_name": "dummy_evaluator",
                                "result": {
                                    "eval_note": 1,
                                    "symbol": "ETH/USDT",
                                    "time_frame": "1h",
                                    "evaluator_name": "DummyEvaluator",
                                    "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
                                    "cryptocurrency": "ETH",
                                },
                            },
                        ],
                    }
                ),
            ):
                with mock.patch.object(
                    FakeEvaluatorAlpha,
                    "get_dsl_dependencies",
                    mock.Mock(return_value=[]),
                ):
                    dependencies = operator.get_dependencies()
        assert dependencies == [
            trading_dsl.SymbolDependency(symbol="BTC/USDT", time_frame="1h"),
            trading_dsl.SymbolDependency(symbol="ETH/USDT", time_frame="1h"),
        ]

    def test_includes_symbol_dependencies_from_dynamic_dependencies_for_strategy_evaluator(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeStrategyEvaluator,
            None,
            {},
            None,
        )
        operator = OpCls()
        with mock.patch(
            "octobot_commons.dsl_interpreter.operator.Operator.get_dependencies",
            mock.Mock(return_value=[]),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                mock.Mock(
                    return_value={
                        evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                        dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY: [
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
                                    "eval_note": -1,
                                    "symbol": "ETH/USDC",
                                    "time_frame": "1h",
                                    "evaluator_name": fake_evaluators.FAKE_DUMMY_EVALUATOR_B,
                                    "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
                                    "cryptocurrency": "ETH",
                                },
                            },
                        ],
                    }
                ),
            ):
                with mock.patch.object(
                    fake_evaluators.FakeStrategyEvaluator,
                    "get_dsl_dependencies",
                    mock.Mock(return_value=[]),
                ):
                    dependencies = operator.get_dependencies()
        assert dependencies == [
            trading_dsl.SymbolDependency(symbol="BTC/USDC", time_frame="1h"),
            trading_dsl.SymbolDependency(symbol="ETH/USDC", time_frame="1h"),
        ]

    def test_returns_symbol_dependency_per_symbol_when_no_time_frames(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            FakeEvaluatorAlpha,
            None,
            {},
            None,
        )
        operator = OpCls()
        with mock.patch(
            "octobot_commons.dsl_interpreter.operator.Operator.get_dependencies",
            mock.Mock(return_value=[]),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                mock.Mock(
                    return_value={
                        evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDT", "ETH/USDT"],
                    }
                ),
            ):
                with mock.patch.object(
                    FakeEvaluatorAlpha,
                    "get_dsl_dependencies",
                    mock.Mock(return_value=[]),
                ):
                    dependencies = operator.get_dependencies()
        assert dependencies == [
            trading_dsl.SymbolDependency(symbol="BTC/USDT"),
            trading_dsl.SymbolDependency(symbol="ETH/USDT"),
        ]


class TestPreCompute:
    @pytest.mark.asyncio
    async def test_raises_when_exchange_manager_is_none(self):
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            FakeEvaluatorAlpha,
            None,
            {},
            "matrix-1",
        )
        operator = OpCls()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                await operator.pre_compute()
        assert "Exchange manager is required" in str(error_info.value)

    @pytest.mark.asyncio
    async def test_raises_when_matrix_id_is_none(self):
        operator, _exchange_manager = _operator_with_exchange_manager(matrix_id=None)
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                await operator.pre_compute()
        assert "Matrix id is required" in str(error_info.value)

    @pytest.mark.asyncio
    async def test_executes_evaluator_and_sets_result_payload(self):
        operator, exchange_manager = _operator_with_exchange_manager()
        fake_evaluator_instance = mock.MagicMock(spec=evaluators.TAEvaluator)
        fake_evaluator_instance.evaluator_type = evaluators_enums.EvaluatorMatrixTypes.TA
        fake_evaluator_instance.get_name.return_value = FakeEvaluatorAlpha.get_name()
        fake_evaluator_instance.get_eval_type.return_value = (
            evaluators_constants.EVALUATOR_EVAL_DEFAULT_TYPE
        )
        fake_evaluator_instance.eval_note = 1
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                evaluator_dsl_factory.evaluator_factory,
                "create_dsl_evaluator",
                mock.AsyncMock(return_value=fake_evaluator_instance),
            ), mock.patch.object(
                operator,
                "_execute_ta_evaluator_via_ohlcv",
                mock.AsyncMock(return_value=1),
            ):
                with mock.patch.object(
                    operator,
                    "get_computed_value_by_parameter",
                    return_value={
                        evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDC"],
                        evaluator_dsl_factory.TIME_FRAMES_PARAM: ["2h"],
                    },
                ):
                    with mock.patch(
                        "octobot_evaluators.evaluators.evaluator_dsl_factory.matrix_manager.set_tentacle_value",
                        mock.Mock(),
                    ):
                        await operator.pre_compute()
        assert operator.value == [{
            "eval_note": 1,
            "eval_note_type": "float",
            "symbol": "BTC/USDC",
            "time_frame": "2h",
            "evaluator_name": "FakeEvaluatorAlpha",
            "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
            "cryptocurrency": "BTC",
        }]


class TestPreComputeTaCartesianProduct:
    @pytest.mark.asyncio
    async def test_executes_evaluator_for_each_symbol_and_time_frame(self):
        operator, exchange_manager = _operator_with_exchange_manager()
        fake_evaluator_instance = mock.MagicMock(spec=evaluators.TAEvaluator)
        fake_evaluator_instance.evaluator_type = evaluators_enums.EvaluatorMatrixTypes.TA
        fake_evaluator_instance.get_name.return_value = FakeEvaluatorAlpha.get_name()
        create_dsl_evaluator_mock = mock.AsyncMock(return_value=fake_evaluator_instance)
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                evaluator_dsl_factory.evaluator_factory,
                "create_dsl_evaluator",
                create_dsl_evaluator_mock,
            ), mock.patch.object(
                operator,
                "_execute_ta_evaluator_via_ohlcv",
                mock.AsyncMock(return_value=1),
            ):
                with mock.patch.object(
                    operator,
                    "get_computed_value_by_parameter",
                    return_value={
                        evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDC", "ETH/USDC"],
                        evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h", "2h"],
                    },
                ):
                    with mock.patch(
                        "octobot_evaluators.evaluators.evaluator_dsl_factory.matrix_manager.set_tentacle_value",
                        mock.Mock(),
                    ):
                        await operator.pre_compute()
        assert create_dsl_evaluator_mock.await_count == 4
        assert len(operator.value) == 4


class TestPreComputeSymbolsAndTimeFramesListValidation:
    @pytest.mark.asyncio
    async def test_raises_when_symbols_is_not_a_list(self):
        operator, _exchange_manager = _operator_with_exchange_manager()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                return_value={
                    evaluator_dsl_factory.SYMBOLS_PARAM: "BTC/USDC",
                    evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                },
            ):
                with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                    await operator.pre_compute()
        assert "symbols must be a list" in str(error_info.value)

    @pytest.mark.asyncio
    async def test_raises_when_time_frames_is_not_a_list(self):
        operator, _exchange_manager = _operator_with_exchange_manager()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                return_value={
                    evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDC"],
                    evaluator_dsl_factory.TIME_FRAMES_PARAM: "1h",
                },
            ):
                with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                    await operator.pre_compute()
        assert "time_frames must be a list" in str(error_info.value)


class TestPreComputeCryptocurrencyValidation:
    @pytest.mark.asyncio
    async def test_raises_when_cryptocurrency_set_with_multiple_symbols(self):
        operator, _exchange_manager = _operator_with_exchange_manager()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                return_value={
                    evaluator_dsl_factory.SYMBOLS_PARAM: ["BTC/USDC", "ETH/USDC"],
                    evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                    evaluator_dsl_factory.CRYPTOCURRENCY_PARAM: "BTC",
                },
            ):
                with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                    await operator.pre_compute()
        assert "Cryptocurrency override is only valid for a single symbol" in str(error_info.value)


def _set_strategy_time_frames(evaluator_instance, _tentacle_config):
    evaluator_instance.strategy_time_frames = [common_enums.TimeFrames.ONE_HOUR]


class TestExecuteStrategyEvaluator:
    @pytest.mark.asyncio
    async def test_calls_matrix_callback_once_with_seeded_matrix(self, matrix_id):
        await evaluator_api.create_evaluator_channels(matrix_id)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binanceus"
        try:
            OpCls = evaluator_dsl_factory.create_evaluator_operator(
                fake_evaluators.FakeMatrixReadingStrategyEvaluator,
                exchange_manager,
                {},
                matrix_id,
            )
            operator = OpCls()
            strategy_instance = fake_evaluators.FakeMatrixReadingStrategyEvaluator(
                evaluator_dsl_factory._get_local_tentacles_setup_config()
            )
            strategy_instance.matrix_id = matrix_id
            strategy_instance.matrix_callback = mock.AsyncMock(
                wraps=strategy_instance.matrix_callback
            )
            for injected_result in (
                evaluator_dsl_factory.EvaluatorResult(
                    symbol="BTC/USDC",
                    time_frame="1h",
                    evaluator_name=fake_evaluators.FAKE_DUMMY_EVALUATOR_A,
                    evaluator_type=evaluators_enums.EvaluatorMatrixTypes.TA.value,
                    cryptocurrency="BTC",
                    eval_note=1,
                ),
                evaluator_dsl_factory.EvaluatorResult(
                    symbol="BTC/USDC",
                    time_frame="1h",
                    evaluator_name=fake_evaluators.FAKE_DUMMY_EVALUATOR_B,
                    evaluator_type=evaluators_enums.EvaluatorMatrixTypes.TA.value,
                    cryptocurrency="BTC",
                    eval_note=-1,
                ),
            ):
                matrix_manager.seed_matrix_from_evaluator_result(
                    matrix_id,
                    exchange_manager.exchange_name,
                    injected_result,
                )
            await operator._execute_strategy_evaluator(
                strategy_instance,
                exchange_manager,
                matrix_id,
                "BTC/USDC",
                "1h",
                "BTC",
            )
            assert strategy_instance.matrix_callback.await_count == 1
        finally:
            evaluator_api.del_evaluator_channels(matrix_id)


class TestPreComputeStrategySymbolsFromDynamicDependencies:
    @pytest.mark.asyncio
    async def test_executes_one_strategy_per_dynamic_dependency_symbol(self, matrix_id):
        await evaluator_api.create_evaluator_channels(matrix_id)
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binanceus"
        matrix_callback_call_count = 0
        original_matrix_callback = (
            fake_evaluators.FakeMatrixReadingStrategyEvaluator.matrix_callback
        )

        async def _create_strategy_instance(*_args, **_kwargs):
            strategy_instance = fake_evaluators.FakeMatrixReadingStrategyEvaluator(
                evaluator_dsl_factory._get_local_tentacles_setup_config()
            )
            strategy_instance.matrix_id = matrix_id
            strategy_instance.evaluator_type = evaluators_enums.EvaluatorMatrixTypes.STRATEGIES
            strategy_instance.strategy_time_frames = [common_enums.TimeFrames.ONE_HOUR]

            async def _counting_matrix_callback(*args, **kwargs):
                nonlocal matrix_callback_call_count
                matrix_callback_call_count += 1
                return await original_matrix_callback(strategy_instance, *args, **kwargs)

            strategy_instance.matrix_callback = _counting_matrix_callback
            return strategy_instance

        try:
            OpCls = evaluator_dsl_factory.create_evaluator_operator(
                fake_evaluators.FakeMatrixReadingStrategyEvaluator,
                exchange_manager,
                {},
                matrix_id,
            )
            operator = OpCls()
            with mock.patch.object(
                dsl_interpreter.PreComputingCallOperator,
                "pre_compute",
                mock.AsyncMock(),
            ):
                with mock.patch.object(
                    evaluator_dsl_factory.evaluator_factory,
                    "create_dsl_evaluator",
                    mock.AsyncMock(side_effect=_create_strategy_instance),
                ):
                    with mock.patch.object(
                        operator,
                        "_init_strategy_time_frames",
                        _set_strategy_time_frames,
                    ):
                        with mock.patch.object(
                            operator,
                            "get_computed_value_by_parameter",
                            return_value={
                                evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                                dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY: [
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
                                            "eval_note": -1,
                                            "symbol": "ETH/USDC",
                                            "time_frame": "1h",
                                            "evaluator_name": fake_evaluators.FAKE_DUMMY_EVALUATOR_B,
                                            "evaluator_type": evaluators_enums.EvaluatorMatrixTypes.TA.value,
                                            "cryptocurrency": "ETH",
                                        },
                                    },
                                ],
                            },
                        ):
                            await operator.pre_compute()
            assert len(operator.value) == 2
            assert {result["symbol"] for result in operator.value} == {"BTC/USDC", "ETH/USDC"}
            assert {result["eval_note"] for result in operator.value} == {1, -1}
            assert matrix_callback_call_count == 2
        finally:
            evaluator_api.del_evaluator_channels(matrix_id)

    @pytest.mark.asyncio
    async def test_raises_when_dynamic_dependencies_provide_no_symbols(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "binanceus"
        OpCls = evaluator_dsl_factory.create_evaluator_operator(
            fake_evaluators.FakeStrategyEvaluator,
            exchange_manager,
            {},
            "matrix-1",
        )
        operator = OpCls()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                operator,
                "get_computed_value_by_parameter",
                return_value={
                    evaluator_dsl_factory.TIME_FRAMES_PARAM: ["1h"],
                    dsl_interpreter.DynamicDependenciesOperatorMixin.DYNAMIC_DEPENDENCIES_KEY: [],
                },
            ):
                with pytest.raises(commons_errors.DSLInterpreterError) as error_info:
                    await operator.pre_compute()
        assert "requires symbols from dynamic dependencies" in str(error_info.value)
