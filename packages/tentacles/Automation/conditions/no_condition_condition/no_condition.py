#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import octobot_commons.configuration as configuration
import octobot.automation.bases.abstract_condition as abstract_condition
import octobot.automation.bases.execution_details as execution_details


class NoCondition(abstract_condition.AbstractCondition):
    async def process(self, execution_details: execution_details.ExecutionDetails) -> bool:
        return True

    @staticmethod
    def get_description() -> str:
        return "Is always passing."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {}

    def apply_config(self, config):
        # no config
        pass
