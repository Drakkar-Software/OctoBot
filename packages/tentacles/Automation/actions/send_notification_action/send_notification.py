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
import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot_services.enums as services_enums
import octobot_services.api as services_api
import octobot.automation.bases.abstract_action as abstract_action
import octobot.automation.bases.execution_details as execution_details


class SendNotification(abstract_action.AbstractAction):
    MESSAGE = "message"

    def __init__(self):
        super().__init__()
        self.notification_message = None

    async def process(
        self, execution_details: execution_details.ExecutionDetails
    ) -> bool:
        await services_api.send_notification(
            services_api.create_notification(
                self.notification_message,
                category=services_enums.NotificationCategory.OTHER
            )
        )
        return True

    @staticmethod
    def get_description() -> str:
        return f"Sends the configured message. " \
               f"Configure notification channels in the 'Accounts' tab. " \
               f"The notification type is '{services_enums.NotificationCategory.OTHER.value.capitalize()}'."

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        return {
            self.MESSAGE: UI.user_input(
                self.MESSAGE, commons_enums.UserInputTypes.TEXT, "Your notification triggered", inputs,
                title="Message to include in your notification.",
                parent_input_name=step_name,
            )
        }

    def apply_config(self, config):
        self.notification_message = config[self.MESSAGE]
