# pylint: disable=missing-class-docstring,missing-function-docstring
#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses
import typing
import time
import asyncio

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges
import octobot_trading.api as trading_api

import tentacles.Meta.DSL_operators.python_std_operators.base_resetting_operators as base_resetting_operators


def _uses_with_open_trades_interval(
    waiting_time: float,
    with_open_trades_seconds: float,
    without_open_trades_seconds: float,
) -> bool:
    return abs(waiting_time - with_open_trades_seconds) <= abs(
        waiting_time - without_open_trades_seconds
    )


def has_open_trades(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> bool:
    if exchange_manager is None:
        raise octobot_commons.errors.InvalidParametersError(
            "recall_when_relevant_for_context() requires an exchange manager context."
        )
    open_orders = trading_api.get_open_orders(exchange_manager, active=None)
    if any(not order.is_cancelled() and not order.is_closed() for order in open_orders):
        return True
    if exchange_manager.is_future:
        positions = trading_api.get_positions(exchange_manager)
        if any(position.size for position in positions):
            return True
    return False


def create_recall_when_relevant_for_context_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager] = None,
) -> list[type[dsl_interpreter.PreComputingCallOperator]]:
    class _RecallWhenRelevantForContextOperator(
        dsl_interpreter.PreComputingCallOperator,
        dsl_interpreter.ReCallableOperatorMixin,
    ):
        NAME = "recall_when_relevant_for_context"
        DESCRIPTION = (
            "Pauses execution using with_open_trades_seconds when open trades exist, "
            "otherwise without_open_trades_seconds. "
            "When return_remaining_time is True, returns the remaining wait as a re-callable result."
        )
        EXAMPLE = "recall_when_relevant_for_context(with_open_trades_seconds=3600, without_open_trades_seconds=14400, return_remaining_time=True)"
        CATEGORY = commons_enums.DslKeywordCategory.TRIGGER.value

        @staticmethod
        def get_library() -> str:
            return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

        @staticmethod
        def get_name() -> str:
            return "recall_when_relevant_for_context"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="with_open_trades_seconds",
                    description="interval in seconds when open trades exist",
                    required=True,
                    type=commons_enums.DslValueType.NUMBER.value,
                ),
                dsl_interpreter.OperatorParameter(
                    name="without_open_trades_seconds",
                    description="interval in seconds when idle (no open trades)",
                    required=True,
                    type=commons_enums.DslValueType.NUMBER.value,
                ),
                dsl_interpreter.OperatorParameter(
                    name="return_remaining_time",
                    description="if True, instantly returns the remaining time to wait",
                    required=False,
                    type=commons_enums.DslValueType.BOOLEAN.value,
                    default=False,
                ),
            ] + [
                dataclasses.replace(parameter)
                for parameter in cls.get_re_callable_parameters()
            ]

        @classmethod
        def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
            return cls.result_return_value(
                commons_enums.DslValueType.ANY.value,
                description="re-callable result with remaining or restarted interval",
            )

        def _selected_interval_seconds(self, param_by_name: dict[str, typing.Any]) -> float:
            with_open_trades_seconds = param_by_name["with_open_trades_seconds"]
            without_open_trades_seconds = param_by_name["without_open_trades_seconds"]
            if with_open_trades_seconds < 0 or without_open_trades_seconds < 0:
                raise octobot_commons.errors.InvalidParametersError(
                    "recall_when_relevant_for_context() requires non-negative interval arguments."
                )
            if has_open_trades(exchange_manager):
                return float(with_open_trades_seconds)
            return float(without_open_trades_seconds)

        def _wait_operator_params(self, param_by_name: dict[str, typing.Any]) -> dict[str, typing.Any]:
            return {
                "min_seconds": self._selected_interval_seconds(param_by_name),
                "max_seconds": None,
                "return_remaining_time": param_by_name["return_remaining_time"],
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY: param_by_name.get(
                    dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
                ),
            }

        def _wait_operator_params_after_interval_change(
            self,
            param_by_name: dict[str, typing.Any],
        ) -> dict[str, typing.Any]:
            last_execution_result = param_by_name.get(
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY
            )
            if last_execution_result is None:
                return self._wait_operator_params(param_by_name)
            last_result = self.get_last_execution_result(param_by_name)
            if last_result is None:
                return self._wait_operator_params(param_by_name)
            with_open_trades_seconds = param_by_name["with_open_trades_seconds"]
            without_open_trades_seconds = param_by_name["without_open_trades_seconds"]
            previous_waiting_time = last_result[
                dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value
            ]
            selected_interval_seconds = self._selected_interval_seconds(param_by_name)
            previously_with_open_trades = _uses_with_open_trades_interval(
                previous_waiting_time,
                with_open_trades_seconds,
                without_open_trades_seconds,
            )
            currently_with_open_trades = _uses_with_open_trades_interval(
                selected_interval_seconds,
                with_open_trades_seconds,
                without_open_trades_seconds,
            )
            if previously_with_open_trades == currently_with_open_trades:
                return self._wait_operator_params(param_by_name)
            reset_param_by_name = dict(param_by_name)
            reset_param_by_name.pop(
                dsl_interpreter.ReCallableOperatorMixin.LAST_EXECUTION_RESULT_KEY,
                None,
            )
            return self._wait_operator_params(reset_param_by_name)

        def _compute_remaining_time(
            self,
            param_by_name: dict[str, typing.Any],
            wait_params: dict[str, typing.Any],
        ) -> typing.Optional[dict[str, typing.Any]]:
            current_time = time.time()
            if last_execution_result := self.get_last_execution_result(wait_params):
                last_execution_time = last_execution_result[
                    dsl_interpreter.ReCallingOperatorResultKeys.LAST_EXECUTION_TIME.value
                ]
                waiting_time = (
                    last_execution_result[dsl_interpreter.ReCallingOperatorResultKeys.WAITING_TIME.value]
                    - (current_time - last_execution_time)
                )
            else:
                waiting_time = wait_params["min_seconds"]
            if waiting_time <= 0:
                waiting_time = wait_params["min_seconds"]
            return self.create_re_callable_result_dict(
                keyword=self.get_name(),
                last_execution_time=current_time,
                waiting_time=waiting_time,
                script_override=self.re_create_script(param_by_name),
            )

        async def pre_compute(self) -> None:
            await super().pre_compute()
            param_by_name = self.get_computed_value_by_parameter()
            wait_params = self._wait_operator_params_after_interval_change(param_by_name)
            if wait_params["return_remaining_time"]:
                self.value = self._compute_remaining_time(param_by_name, wait_params)
            else:
                wait_operator = base_resetting_operators.WaitOperator(1)
                await asyncio.sleep(wait_operator._compute_sleep_time(wait_params))
                self.value = None

    return [_RecallWhenRelevantForContextOperator]
