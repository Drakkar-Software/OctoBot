#  Drakkar-Software OctoBot-Trading
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
import pytest
import mock

import octobot_commons.configuration.user_inputs as user_inputs
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.enums as common_enums
import octobot_commons.errors as commons_errors
import octobot_commons.str_util as str_util

import octobot_trading.modes.mode_dsl_factory as trading_mode_dsl_factory


pytestmark = pytest.mark.asyncio

_TENTACLE_TYPE = common_enums.UserInputTentacleTypes.TRADING_MODE.value


def _make_user_input(
    name,
    input_type,
    def_val,
    value=None,
    title=None,
    parent_input_name=None,
):
    return user_inputs.UserInput(
        name=name,
        input_type=input_type,
        value=value if value is not None else def_val,
        def_val=def_val,
        tentacle_type=_TENTACLE_TYPE,
        tentacle_name="FakeMode",
        title=title,
        parent_input_name=parent_input_name,
    )


class FakeTradingModeAlpha:
    @classmethod
    def get_name(cls) -> str:
        return "FakeTradingModeAlpha"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        instance = mock.Mock()
        instance.synchronous_execution = False

        def init_user_inputs(inputs):
            inputs["skip_str"] = "not a UserInput"
            inputs["nested"] = _make_user_input(
                "Nested",
                common_enums.UserInputTypes.TEXT.value,
                "x",
                parent_input_name="parent",
            )
            inputs["top_int"] = _make_user_input(
                "Top Level Int",
                common_enums.UserInputTypes.INT.value,
                0,
                title="Integer setting",
            )
            inputs["top_float_enum"] = _make_user_input(
                "Top Float",
                common_enums.UserInputTypes.FLOAT,
                1.5,
            )

        instance.init_user_inputs = init_user_inputs
        return instance


class FakeTradingModeBeta:
    @classmethod
    def get_name(cls) -> str:
        return "FakeTradingModeBeta"

    @classmethod
    def create_local_instance(cls, config, tentacles_setup_config, loaded_config):
        instance = mock.Mock()
        instance.synchronous_execution = False
        instance.init_user_inputs = lambda inputs: None
        return instance


class FakeTradingModeWithDslDeps(FakeTradingModeAlpha):
    @classmethod
    def get_dsl_dependencies(cls, trading_config, config):
        return [dsl_interpreter.InterpreterDependency()]


def _trading_mode_mock(
    *,
    waiting_time=3600.0,
    dsl_state=None,
    supports_portfolio_optimization=False,
    name="MockTradingMode",
):
    m = mock.Mock()
    m.manual_trigger = mock.AsyncMock()
    m.get_time_before_next_execution = mock.Mock(return_value=waiting_time)
    m.get_dsl_state = mock.Mock(return_value={} if dsl_state is None else dsl_state)
    m.SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION = supports_portfolio_optimization
    m.get_name = mock.Mock(return_value=name)
    return m


def _operator_with_exchange_manager():
    exchange_manager = mock.Mock()
    op_cls = trading_mode_dsl_factory.create_trading_mode_operator(
        FakeTradingModeBeta,
        exchange_manager,
        {"profile": True},
    )
    return op_cls(), exchange_manager


class TestCreateOperatorParametersFromUserInputs:
    def test_empty(self):
        assert trading_mode_dsl_factory._create_operator_parameters_from_user_inputs({}) == []

    def test_skips_non_user_input(self):
        created = {"x": "skip", "y": 3}
        assert trading_mode_dsl_factory._create_operator_parameters_from_user_inputs(created) == []

    def test_skips_nested(self):
        created = {
            "n": _make_user_input(
                "child",
                common_enums.UserInputTypes.BOOLEAN.value,
                False,
                parent_input_name="root",
            ),
        }
        assert trading_mode_dsl_factory._create_operator_parameters_from_user_inputs(created) == []

    def test_top_level_string_input_type(self):
        ui = _make_user_input(
            "My Setting Name",
            common_enums.UserInputTypes.TEXT.value,
            "d",
            title="Shown title",
        )
        params = trading_mode_dsl_factory._create_operator_parameters_from_user_inputs({"a": ui})
        assert len(params) == 1
        p = params[0]
        assert p.name == user_inputs.sanitize_user_input_name(ui.name)
        assert p.type is str
        assert p.default == "d"
        assert p.description == "Shown title"
        assert p.required is False

    def test_top_level_enum_input_type(self):
        ui = _make_user_input(
            "float_param",
            common_enums.UserInputTypes.FLOAT,
            2.0,
        )
        params = trading_mode_dsl_factory._create_operator_parameters_from_user_inputs({"f": ui})
        assert len(params) == 1
        assert params[0].type is float
        assert params[0].default == 2.0
        assert params[0].description == "float_param"


class TestCreateTradingModeOperatorParameters:
    def test_derives_parameters_from_init_user_inputs(self):
        params = trading_mode_dsl_factory._create_trading_mode_operator_parameters(
            FakeTradingModeAlpha,
            {"bot": True},
        )
        names = {p.name for p in params}
        assert "Top_Level_Int" in names
        assert "Top_Float" in names
        assert "Nested" not in names
        int_param = next(p for p in params if p.name == "Top_Level_Int")
        assert int_param.type is int
        assert int_param.description == "Integer setting"


class TestCreateTradingModeOperator:
    def test_name_metadata_and_context_getters(self):
        em = mock.Mock()
        cfg = {"x": 1}
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeAlpha,
            em,
            cfg,
        )
        assert OpCls.get_name() == str_util.camel_to_snake(FakeTradingModeAlpha.get_name())
        assert FakeTradingModeAlpha.get_name() in OpCls.DESCRIPTION
        assert OpCls.EXAMPLE == f"{OpCls.get_name()}()"
        op = OpCls()
        assert op.get_exchange_manager() is em
        assert op.get_trading_mode_class() is FakeTradingModeAlpha
        assert op.get_config() is cfg


class TestGetParameters:
    def test_lazy_list_stable_across_calls(self):
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeAlpha,
            mock.Mock(),
            {},
        )
        first = OpCls.get_parameters()
        second = OpCls.get_parameters()
        assert [p.name for p in first] == [p.name for p in second]
        trading_param_names = {
            p.name
            for p in first
            if p.name != dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
        }
        assert trading_param_names == {"Top_Level_Int", "Top_Float"}
        assert sum(
            1 for p in first if p.name == dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
        ) == 1


class TestGetResultsSummary:
    def test_empty_and_no_last_execution_result(self):
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeBeta,
            None,
            {},
        )
        op = OpCls()
        summary = op.get_results_summary([])
        inner = summary[dsl_interpreter.ReCallingOperatorResult.__name__]
        assert inner["last_execution_result"][
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ] is None
        assert inner["last_execution_result"][
            dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
        ] is None

        no_payload = dsl_interpreter.ReCallingOperatorResult(last_execution_result=None)
        summary2 = op.get_results_summary([no_payload])
        inner2 = summary2[dsl_interpreter.ReCallingOperatorResult.__name__]
        assert inner2["last_execution_result"][
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
        ] is None

    def test_picks_minimum_waiting_time(self):
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeBeta,
            None,
            {},
        )
        op = OpCls()
        r1 = dsl_interpreter.ReCallingOperatorResult(
            last_execution_result={
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 30.0,
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 100.0,
            },
        )
        r2 = dsl_interpreter.ReCallingOperatorResult(
            last_execution_result={
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 10.0,
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 200.0,
            },
        )
        summary = op.get_results_summary([r1, r2])
        inner = summary[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert inner[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 10.0
        assert inner[dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value] == 200.0

    def test_merged_state_last_wins(self):
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeBeta,
            None,
            {},
        )
        op = OpCls()
        r1 = dsl_interpreter.ReCallingOperatorResult(
            last_execution_result={
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1.0,
                "custom": "first",
                "other": "a",
            },
        )
        r2 = dsl_interpreter.ReCallingOperatorResult(
            last_execution_result={
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 10.0,
                dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 2.0,
                "custom": "second",
                "other2": "b",
            },
        )
        summary = op.get_results_summary([r1, r2])
        inner = summary[dsl_interpreter.ReCallingOperatorResult.__name__]["last_execution_result"]
        assert inner["state"] == {
            dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value: 10.0,
            dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 2.0,
            "custom": "second",
            "other": "a",
            "other2": "b",
        }


class TestGetDependencies:
    def test_merges_super_and_trading_mode(self):
        base_dep = dsl_interpreter.InterpreterDependency()
        local_dep = dsl_interpreter.InterpreterDependency()
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeWithDslDeps,
            None,
            {"global": True},
        )
        op = OpCls()
        with mock.patch(
            "octobot_commons.dsl_interpreter.operator.Operator.get_dependencies",
            mock.Mock(return_value=[base_dep]),
        ):
            with mock.patch.object(
                op,
                "get_computed_value_by_parameter",
                mock.Mock(return_value={"param": 1}),
            ):
                with mock.patch.object(
                    FakeTradingModeWithDslDeps,
                    "get_dsl_dependencies",
                    mock.Mock(return_value=[local_dep]),
                ) as gdd:
                    deps = op.get_dependencies()
                    # Mock replaces the classmethod descriptor; calls are (trading_config, config).
                    gdd.assert_called_once_with({"param": 1}, {"global": True})
        assert deps == [base_dep, local_dep]


class TestCreateAllTradingModeOperators:
    def test_builds_one_operator_per_trading_mode_class(self):
        with mock.patch(
            "octobot_trading.modes.mode_dsl_factory.modes_factory.get_all_concrete_trading_mode_classes",
            return_value=(FakeTradingModeAlpha, FakeTradingModeBeta),
        ):
            ops = trading_mode_dsl_factory.create_all_trading_mode_operators(
                mock.sentinel.em,
                {"c": 2},
            )
        assert len(ops) == 2
        names = {cls.get_name() for cls in ops}
        assert names == {
            str_util.camel_to_snake(FakeTradingModeAlpha.get_name()),
            str_util.camel_to_snake(FakeTradingModeBeta.get_name()),
        }
        modes_wrapped = {op_cls().get_trading_mode_class() for op_cls in ops}
        assert modes_wrapped == {FakeTradingModeAlpha, FakeTradingModeBeta}
        for op_cls in ops:
            inst = op_cls()
            assert inst.get_exchange_manager() is mock.sentinel.em
            assert inst.get_config() == {"c": 2}


class TestPreCompute:
    async def test_raises_when_exchange_manager_is_none(self):
        OpCls = trading_mode_dsl_factory.create_trading_mode_operator(
            FakeTradingModeBeta,
            None,
            {},
        )
        op = OpCls()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            new_callable=mock.AsyncMock,
        ):
            with pytest.raises(commons_errors.DSLInterpreterError) as excinfo:
                await op.pre_compute()
        assert "Exchange manager is required" in str(excinfo.value)

    async def test_sets_value_and_invokes_manual_trigger_for_each_mode(self):
        op, em = _operator_with_exchange_manager()
        tm_a = _trading_mode_mock(waiting_time=10.0, dsl_state={"id": "a"}, name="A")
        tm_b = _trading_mode_mock(waiting_time=20.0, dsl_state={"id": "b"}, name="B")
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                op,
                "get_computed_value_by_parameter",
                return_value={"qty": 1},
            ):
                with mock.patch.object(
                    op,
                    "get_last_execution_result",
                    return_value={"prior": True},
                ):
                    with mock.patch.object(
                        op,
                        "_optimize_initial_portfolio",
                        mock.AsyncMock(),
                    ) as optimize_mock:
                        with mock.patch.object(
                            op,
                            "_create_trading_modes",
                            mock.AsyncMock(return_value=[tm_a, tm_b]),
                        ) as create_mock:
                            await op.pre_compute()
        optimize_mock.assert_not_awaited()
        create_mock.assert_awaited_once_with(
            FakeTradingModeBeta,
            {"qty": 1},
            em,
        )
        tm_a.manual_trigger.assert_awaited_once_with(
            {"trigger_source": common_enums.TriggerSource.MANUAL.value},
        )
        tm_b.manual_trigger.assert_awaited_once_with(
            {"trigger_source": common_enums.TriggerSource.MANUAL.value},
        )
        assert op.value is not dsl_interpreter.UNINITIALIZED_VALUE
        inner = op.value[dsl_interpreter.ReCallingOperatorResult.__name__][
            "last_execution_result"
        ]
        assert inner[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 10.0
        # summary passes merged per-mode results as `state=`; nested DSL state is under "state".
        assert inner["state"][dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value] == 20.0
        assert inner["state"]["state"]["id"] == "b"

    async def test_calls_optimize_initial_portfolio_on_first_execution(self):
        op, em = _operator_with_exchange_manager()
        tm = _trading_mode_mock()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                op,
                "get_computed_value_by_parameter",
                return_value={},
            ):
                with mock.patch.object(
                    op,
                    "_create_trading_modes",
                    mock.AsyncMock(return_value=[tm]),
                ):
                    with mock.patch.object(
                        op,
                        "_optimize_initial_portfolio",
                        mock.AsyncMock(),
                    ) as optimize_mock:
                        await op.pre_compute()
        optimize_mock.assert_awaited_once_with([tm], [], {})

    async def test_skips_optimize_when_get_last_execution_result_truthy(self):
        op, em = _operator_with_exchange_manager()
        tm = _trading_mode_mock()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                op,
                "get_computed_value_by_parameter",
                return_value={},
            ):
                with mock.patch.object(
                    op,
                    "get_last_execution_result",
                    return_value={"waiting_time": 5.0},
                ):
                    with mock.patch.object(
                        op,
                        "_create_trading_modes",
                        mock.AsyncMock(return_value=[tm]),
                    ):
                        with mock.patch.object(
                            op,
                            "_optimize_initial_portfolio",
                            mock.AsyncMock(),
                        ) as optimize_mock:
                            await op.pre_compute()
        optimize_mock.assert_not_awaited()

    async def test_optimize_failure_is_logged_and_execution_continues(self):
        op, em = _operator_with_exchange_manager()
        tm = _trading_mode_mock()
        logger = mock.Mock()
        with mock.patch.object(
            dsl_interpreter.PreComputingCallOperator,
            "pre_compute",
            mock.AsyncMock(),
        ):
            with mock.patch.object(
                op,
                "get_computed_value_by_parameter",
                return_value={},
            ):
                with mock.patch.object(
                    op,
                    "_create_trading_modes",
                    mock.AsyncMock(return_value=[tm]),
                ):
                    with mock.patch.object(
                        op,
                        "_optimize_initial_portfolio",
                        mock.AsyncMock(side_effect=RuntimeError("optimize failed")),
                    ):
                        with mock.patch.object(
                            op,
                            "_get_logger",
                            return_value=logger,
                        ):
                            await op.pre_compute()
        logger.exception.assert_called_once()
        tm.manual_trigger.assert_awaited_once()
        assert op.value is not dsl_interpreter.UNINITIALIZED_VALUE


class TestOptimizeInitialPortfolio:
    async def test_returns_early_when_mode_does_not_support_optimization(self):
        op, _em = _operator_with_exchange_manager()
        tm = _trading_mode_mock(supports_portfolio_optimization=False)
        logger = mock.Mock()
        with mock.patch.object(op, "_get_logger", return_value=logger):
            await op._optimize_initial_portfolio([tm], [], {})
        logger.info.assert_called_once()
        assert "does not support initial" in logger.info.call_args[0][0]
        tm.optimize_initial_portfolio.assert_not_called()

    async def test_calls_optimize_when_mode_supports_it(self):
        op, em = _operator_with_exchange_manager()
        tm = _trading_mode_mock(supports_portfolio_optimization=True)
        tm.optimize_initial_portfolio = mock.AsyncMock()
        portfolio_holder = mock.Mock()
        em.exchange_personal_data.portfolio_manager.portfolio.portfolio = portfolio_holder
        with mock.patch(
            "octobot_trading.modes.mode_dsl_factory.personal_data.portfolio_to_float",
            return_value={},
        ):
            with mock.patch(
                "octobot_trading.modes.mode_dsl_factory.personal_data.get_balance_summary",
                return_value="summary",
            ):
                with mock.patch.object(op, "_get_logger", return_value=mock.Mock()):
                    await op._optimize_initial_portfolio(
                        [tm],
                        mock.sentinel.sellable,
                        mock.sentinel.tickers,
                    )
        tm.optimize_initial_portfolio.assert_awaited_once_with(
            mock.sentinel.sellable,
            mock.sentinel.tickers,
        )
