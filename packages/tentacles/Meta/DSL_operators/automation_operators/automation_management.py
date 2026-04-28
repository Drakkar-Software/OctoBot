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
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_commons.dsl_interpreter.operator_parameter as operator_parameter

import octobot_flow.entities


class StopAutomationOperator(dsl_interpreter.CallOperator):
    MIN_PARAMS = 0
    MAX_PARAMS = 0
    DESCRIPTION = "Signals the automation to stop."
    EXAMPLE = "stop_automation()"

    @staticmethod
    def get_name() -> str:
        return "stop_automation"

    def compute(self) -> dict:
        return {
            octobot_flow.entities.PostIterationActionsDetails.__name__:
            octobot_flow.entities.PostIterationActionsDetails(
                stop_automation=True
            ).to_dict(include_default_values=False)
        }


class UpdateAutomationConfigurationOperator(dsl_interpreter.CallOperator):
    DESCRIPTION = (
        "Requests a configuration refresh for the automation. Pass the full replacement DSL "
        "script for the DAG action that must be the only executable action at this point; the "
        "executor sets that action's `dsl_script` and then runs the refresh signal (e.g. restart "
        "for process-bound operators). This is not limited to `run_octobot_process`—any "
        "executable DSL action can be retargeted."
    )
    EXAMPLE = 'update_automation_configuration("your_dsl_call(...)")'

    @staticmethod
    def get_name() -> str:
        return "update_automation_configuration"

    @classmethod
    def get_parameters(cls) -> list[operator_parameter.OperatorParameter]:
        return [
            operator_parameter.OperatorParameter(
                name="configuration_update",
                description=(
                    "Full replacement DSL for the single currently executable DAG script action "
                    "(becomes that action's `dsl_script`). Any operator form is valid as long as "
                    "it matches the action being updated (e.g. `run_octobot_process(...)`, "
                    "exchange calls, etc.)."
                ),
                required=True,
                type=str,
                default=None,
            ),
        ]

    def compute(self) -> dict:
        configuration_update = self.get_computed_value_by_parameter()["configuration_update"]
        return {
            octobot_flow.entities.PostIterationActionsDetails.__name__:
            octobot_flow.entities.PostIterationActionsDetails(
                configuration_update=configuration_update,
            ).to_dict(include_default_values=False)
        }
