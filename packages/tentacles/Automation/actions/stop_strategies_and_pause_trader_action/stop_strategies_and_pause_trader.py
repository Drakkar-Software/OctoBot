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
import octobot_services.interfaces.util as interfaces_util
import octobot_commons.configuration as configuration
import octobot_commons.enums as commons_enums
import octobot.automation.bases.abstract_action as abstract_action
import octobot.automation.bases.execution_details as execution_details


class StopStrategiesAndPauseTrader(abstract_action.AbstractAction):
    STOP_REASON = "stop_reason"

    def __init__(self):
        super().__init__()
        self.stop_reason = commons_enums.StopReason.STOP_CONDITION_TRIGGERED

    @staticmethod
    def get_description() -> str:
        return "Stop all strategies, clear their state and pause traders."

    def get_user_inputs(
        self, UI: configuration.UserInputFactory, inputs: dict, step_name: str
    ) -> dict:
        return {
            self.STOP_REASON: UI.user_input(
                self.STOP_REASON, commons_enums.UserInputTypes.OPTIONS, commons_enums.StopReason.STOP_CONDITION_TRIGGERED.value, inputs,
                options=[stop_reason.value for stop_reason in commons_enums.StopReason],
                title="Stop reason: the reason for stopping the strategies and pausing the traders.",
                parent_input_name=step_name,
            )
        }

    def apply_config(self, config: dict):
        self.stop_reason = commons_enums.StopReason(config.get(self.STOP_REASON, commons_enums.StopReason.STOP_CONDITION_TRIGGERED.value))

    async def process(
        self, execution_details: execution_details.ExecutionDetails
    ) -> bool:
        await interfaces_util.get_bot_api().stop_all_trading_modes_and_pause_traders(
            self.stop_reason,
            execution_details=execution_details.get_initial_execution_details(),
            schedule_bot_stop=False,
        )
        return True
