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
