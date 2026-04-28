#  Drakkar-Software OctoBot-Commons
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
import time

import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.dsl_interpreter.operator_parameter as operator_parameter
import octobot_commons.dsl_interpreter.operators.re_callable_operator_mixin as re_callable_operator_mixin


class TestReCallingOperatorResult:
    def test_is_re_calling_operator_result_with_reset_to_id(self):
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result(
            {re_callable_operator_mixin.ReCallingOperatorResult.__name__: {"reset_to_id": "some_id"}}
        ) is True

    def test_is_re_calling_operator_result_with_last_execution_result(self):
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result(
            {
                re_callable_operator_mixin.ReCallingOperatorResult.__name__: {
                    "last_execution_result": {"waiting_time": 5, "last_execution_time": 1000.0},
                }
            }
        ) is True

    def test_is_re_calling_operator_result_false_for_non_dict(self):
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result(None) is False
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result([]) is False
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result("str") is False

    def test_is_re_calling_operator_result_false_for_dict_without_keys(self):
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result({}) is False
        assert re_callable_operator_mixin.ReCallingOperatorResult.is_re_calling_operator_result(
            {"other_key": "value"}
        ) is False

    def test_get_next_call_time_with_full_data(self):
        with mock.patch.object(time, "time", return_value=1000.0):
            result = re_callable_operator_mixin.ReCallingOperatorResult(
                reset_to_id=None,
                last_execution_result={
                    re_callable_operator_mixin.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                    re_callable_operator_mixin.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
                },
            )
            assert result.get_next_call_time() == 1005.0

    def test_get_next_call_time_with_missing_last_execution_time_uses_current_time(self):
        with mock.patch.object(time, "time", return_value=2000.0):
            result = re_callable_operator_mixin.ReCallingOperatorResult(
                reset_to_id=None,
                last_execution_result={
                    re_callable_operator_mixin.ReCallingOperatorResultKeys.WAITING_TIME.value: 10.0,
                },
            )
            assert result.get_next_call_time() == 2010.0

    def test_get_next_call_time_returns_none_when_no_last_execution_result(self):
        result = re_callable_operator_mixin.ReCallingOperatorResult(
            reset_to_id=None,
            last_execution_result=None,
        )
        assert result.get_next_call_time() is None

    def test_get_next_call_time_returns_none_when_waiting_time_is_zero(self):
        result = re_callable_operator_mixin.ReCallingOperatorResult(
            reset_to_id=None,
            last_execution_result={
                re_callable_operator_mixin.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
                re_callable_operator_mixin.ReCallingOperatorResultKeys.WAITING_TIME.value: 0,
            },
        )
        assert result.get_next_call_time() is None


class _TestReCallableOperator(dsl_interpreter.ReCallableOperatorMixin):
    """Minimal operator using the mixin for testing."""

    def __init__(self):
        pass

    @staticmethod
    def get_name() -> str:
        return "test_recallable_minimal"




class _ReCreateScriptTestOperator(dsl_interpreter.Operator, dsl_interpreter.ReCallableOperatorMixin):
    """Operator with parameters so re_create_script can call resove_operator_params."""

    @staticmethod
    def get_name() -> str:
        return "test_wait"

    @classmethod
    def get_parameters(cls):
        return [
            operator_parameter.OperatorParameter(
                name="seconds",
                description="wait duration",
                required=True,
                type=float,
            ),
            operator_parameter.OperatorParameter(
                name="label",
                description="optional label",
                required=False,
                type=str,
            ),
        ]

    def compute(self):
        return None


class TestReCallableOperatorMixin:
    def test_last_execution_result_key(self):
        assert dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY == "last_execution_result"

    def test_get_re_callable_parameters(self):
        params = dsl_interpreter.ReCallableOperatorMixin.get_re_callable_parameters()
        assert len(params) == 1
        assert params[0].name == "last_execution_result"
        assert params[0].required is False
        assert params[0].default is None

    def test_get_last_execution_result_returns_none_when_param_missing(self):
        operator = _TestReCallableOperator()
        assert operator.get_last_execution_result({}) is None
        assert operator.get_last_execution_result({"other": "value"}) is None

    def test_get_last_execution_result_returns_none_when_param_is_none(self):
        operator = _TestReCallableOperator()
        assert operator.get_last_execution_result({
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: None,
        }) is None

    def test_get_last_execution_result_returns_none_when_not_re_calling_format(self):
        operator = _TestReCallableOperator()
        assert operator.get_last_execution_result({
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {"wrong": "structure"},
        }) is None

    def test_get_last_execution_result_returns_inner_dict_for_valid_format(self):
        operator = _TestReCallableOperator()
        inner = {
            re_callable_operator_mixin.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value: 1000.0,
            re_callable_operator_mixin.ReCallingOperatorResultKeys.WAITING_TIME.value: 5.0,
        }
        result = operator.get_last_execution_result({
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                re_callable_operator_mixin.ReCallingOperatorResult.__name__: {
                    "last_execution_result": inner,
                },
            },
        })
        assert result == inner

    def test_get_last_execution_result_with_reset_to_id_format(self):
        operator = _TestReCallableOperator()
        inner = {"waiting_time": 3.0, "last_execution_time": 500.0}
        result = operator.get_last_execution_result({
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                re_callable_operator_mixin.ReCallingOperatorResult.__name__: {
                    "reset_to_id": "abc",
                    "last_execution_result": inner,
                },
            },
        })
        assert result == inner

    def test_create_re_callable_result_dict(self):
        operator = _TestReCallableOperator()
        result = operator.create_re_callable_result_dict(
            keyword="recall",
            last_execution_time=1000.0,
            waiting_time=5.0,
        )
        inner = result[re_callable_operator_mixin.ReCallingOperatorResult.__name__]
        assert inner["keyword"] == "recall"
        assert "last_execution_result" in inner
        assert inner["last_execution_result"][
            re_callable_operator_mixin.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
        ] == 1000.0
        assert inner["last_execution_result"][
            re_callable_operator_mixin.ReCallingOperatorResultKeys.WAITING_TIME.value
        ] == 5.0

    def test_create_re_callable_result_dict_with_reset_to_id(self):
        operator = _TestReCallableOperator()
        result = operator.create_re_callable_result_dict(
            keyword="recall",
            reset_to_id="target_123",
            last_execution_time=1000.0,
            waiting_time=5.0,
        )
        inner = result[re_callable_operator_mixin.ReCallingOperatorResult.__name__]
        assert inner["reset_to_id"] == "target_123"
        assert "last_execution_result" in inner

    def test_create_re_callable_result_dict_with_extra_kwargs(self):
        operator = _TestReCallableOperator()
        result = operator.create_re_callable_result_dict(
            keyword="recall",
            last_execution_time=1000.0,
            waiting_time=5.0,
            extra_field=42,
        )
        inner = result[re_callable_operator_mixin.ReCallingOperatorResult.__name__]
        assert inner["last_execution_result"]["extra_field"] == 42

    def test_re_create_script_drops_last_execution_result_and_formats_params(self):
        operator = _ReCreateScriptTestOperator(0.0)
        previous_call_payload = {
            re_callable_operator_mixin.ReCallingOperatorResult.__name__: {
                "keyword": "recall",
                "last_execution_result": {"waiting_time": 1.0},
            },
        }
        script = operator.re_create_script({
            "seconds": 9.0,
            "label": "retry",
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: previous_call_payload,
        })
        assert script == "test_wait(9.0, label='retry')"
        assert dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY not in script

    def test_re_create_script_with_only_last_execution_result_yields_empty_call(self):
        operator = _ReCreateScriptTestOperator(1.0)
        script = operator.re_create_script({
            dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: {
                re_callable_operator_mixin.ReCallingOperatorResult.__name__: {},
            },
        })
        assert script == "test_wait()"

    def test_re_create_script_required_only(self):
        operator = _ReCreateScriptTestOperator(0.0)
        script = operator.re_create_script({"seconds": 42})
        assert script == "test_wait(42)"
