#  Drakkar-Software OctoBot-Node
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
import dataclasses

import octobot_commons.dataclasses.minimizable_dataclass
import octobot_protocol.models as protocol_models

import octobot_node.scheduler.user_actions.user_actions_executor as user_actions_executor


@dataclasses.dataclass
class UserActionWorkflowInputs(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    wallet_address: str
    user_action: protocol_models.UserAction


@dataclasses.dataclass
class UserActionWorkflowOutput(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    wallet_address: str
    updated_user_action: protocol_models.UserAction


@dataclasses.dataclass
class UserActionExecutionResult(octobot_commons.dataclasses.minimizable_dataclass.MinimizableDataclass):
    updated_user_action: protocol_models.UserAction
    post_actions: user_actions_executor.UserActionPostActions
