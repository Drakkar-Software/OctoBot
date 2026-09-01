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
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.signals
import octobot_trading.exchanges
import octobot_trading.modes.abstract_trading_mode

import octobot_flow.entities


def create_stop_automation_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
    trading_mode: typing.Optional[octobot_trading.modes.abstract_trading_mode.AbstractTradingMode] = None,
    dependencies: typing.Optional[octobot_commons.signals.SignalDependencies] = None,
    wait_for_cancelling: bool = True,
) -> list:

    class _StopAutomationOperator(dsl_interpreter.CallOperator):
        DESCRIPTION = "Signals the automation to stop."
        EXAMPLE = "stop_automation(cancel_orders=True)"
        CATEGORY = commons_enums.DslKeywordCategory.ACTION.value

        @staticmethod
        def get_name() -> str:
            return "stop_automation"

        @staticmethod
        def get_library() -> str:
            return commons_constants.CONTEXTUAL_OPERATORS_LIBRARY

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                dsl_interpreter.OperatorParameter(
                    name="cancel_orders",
                    description="When true, cancel all open orders before stopping (flow automations only).",
                    required=False,
                    type=commons_enums.DslValueType.BOOLEAN.value,
                    default=False,
                ),
            ]

        @classmethod
        def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
            return cls.result_return_value(
                commons_enums.DslValueType.DICT.value,
                description="Automation stop signal",
            )

        async def pre_compute(self) -> None:
            await super().pre_compute()
            param_by_name = self.get_computed_value_by_parameter()
            if not param_by_name.get("cancel_orders"):
                return
            if exchange_manager is None:
                return
            to_cancel = [
                order
                for order in exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                    active=None
                )
                if not (order.is_cancelled() or order.is_closed())
            ]
            for order in to_cancel:
                if trading_mode:
                    await trading_mode.cancel_order(
                        order, wait_for_cancelling=wait_for_cancelling, dependencies=dependencies
                    )
                else:
                    await exchange_manager.trader.cancel_order(
                        order, wait_for_cancelling=wait_for_cancelling
                    )

        def compute(self) -> dict:
            return {
                octobot_flow.entities.PostIterationActionsDetails.__name__:
                octobot_flow.entities.PostIterationActionsDetails(
                    stop_automation=True
                ).to_dict(include_default_values=False)
            }

    return [
        _StopAutomationOperator,
    ]


class UpdateAutomationConfigurationOperator(dsl_interpreter.CallOperator):
    DESCRIPTION = (
        "Requests a configuration refresh for the automation. Pass the full replacement DSL "
        "script for the DAG action that must be the only executable action at this point; the "
        "executor sets that action's `dsl_script` and then runs the refresh signal (e.g. restart "
        "for process-bound operators). This is not limited to `run_octobot_process`—any "
        "executable DSL action can be retargeted."
    )
    EXAMPLE = 'update_automation_configuration("your_dsl_call(...)")'
    CATEGORY = commons_enums.DslKeywordCategory.ACTION.value

    @staticmethod
    def get_name() -> str:
        return "update_automation_configuration"

    @classmethod
    def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(
                name="configuration_update",
                description=(
                    "Full replacement DSL for the single currently executable DAG script action "
                    "(becomes that action's `dsl_script`). Any operator form is valid as long as "
                    "it matches the action being updated (e.g. `run_octobot_process(...)`, "
                    "exchange calls, etc.)."
                ),
                required=True,
                type=commons_enums.DslValueType.TEXT.value,
                default=None,
            ),
        ]

    @classmethod
    def get_return_values(cls) -> list[dsl_interpreter.OperatorParameter]:
        return cls.result_return_value(
            commons_enums.DslValueType.DICT.value,
            description="Automation configuration update signal",
        )

    def compute(self) -> dict:
        configuration_update = self.get_computed_value_by_parameter()["configuration_update"]
        return {
            octobot_flow.entities.PostIterationActionsDetails.__name__:
            octobot_flow.entities.PostIterationActionsDetails(
                configuration_update=configuration_update,
            ).to_dict(include_default_values=False)
        }
