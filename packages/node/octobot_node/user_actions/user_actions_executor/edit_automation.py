#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import octobot_protocol.models as protocol_models

import octobot_node.user_actions.user_actions_executor.automation_user_action_executor as automation_user_action_executor


class EditAutomationActionExecutor(automation_user_action_executor.AutomationUserActionExecutor):
    async def _do_execute(
        self,
        user_action: protocol_models.UserAction,
    ) -> None:
        raise ValueError(
            "User action automation_edit is not supported yet by the node user-action translator."
        )
