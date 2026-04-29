#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import copy
import typing
import time
import octobot_commons.logging as logging
import octobot_commons.configuration as configuration

import octobot.automation.bases.execution_details as execution_details


def last_execution_details_updater(func):
    async def last_execution_details_updater_wrapper(self, *args, **kwargs):
        if result := await func(self, *args, **kwargs):
            self.update_last_execution_details()
        return result
    return last_execution_details_updater_wrapper


class AutomationStep:
    def __init__(self):
        self.logger = logging.get_logger(self.get_name())
        self.last_execution_details: execution_details.ExecutionDetails = execution_details.ExecutionDetails(
            timestamp=0,
            description=None,
            source=None,
        )

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def get_description(cls) -> str:
        raise NotImplementedError(f"get_description is not implemented for {cls.get_name()}")

    def get_execution_description(self) -> typing.Optional[str]:
        return None

    def get_user_inputs(self, UI: configuration.UserInputFactory, inputs: dict, step_name: str) -> dict:
        raise NotImplementedError(f"get_user_inputs is not implemented for {self.get_name()}")

    def apply_config(self, config):
        raise NotImplementedError(f"apply_config is not implemented for {self.get_name()}")

    def update_last_execution_details(
        self,
        description: typing.Optional[str] = None,
        source: typing.Optional[execution_details.ExecutionDetails] = None,
    ):
        self.last_execution_details.timestamp = time.time()
        self.last_execution_details.description = description or self.get_execution_description()
         # avoid modifying the source if it's executed again
        self.last_execution_details.source = copy.deepcopy(source)
