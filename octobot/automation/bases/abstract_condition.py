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
import abc

import octobot.automation.bases.automation_step as automation_step
import octobot.automation.bases.execution_details as execution_details


class AbstractCondition(automation_step.AutomationStep, abc.ABC):
    @automation_step.last_execution_details_updater
    async def call_process(self, execution_details: execution_details.ExecutionDetails) -> bool:
        return await self.process(execution_details)

    async def process(
        self, execution_details: execution_details.ExecutionDetails
    ) -> bool:
        raise NotImplementedError
