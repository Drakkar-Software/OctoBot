#  Drakkar-Software OctoBot-Tentacles
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

from .default_manager_agent import (
    DefaultTeamManagerAgentProducer,
    DefaultTeamManagerAgentChannel,
    DefaultTeamManagerAgentConsumer,
)
from .ai_plan_manager_agent import (
    AIPlanTeamManagerAgentProducer,
    AIPlanTeamManagerAgentChannel,
    AIPlanTeamManagerAgentConsumer,
)
from .ai_tools_manager_agent import (
    AIToolsTeamManagerAgentProducer,
    AIToolsTeamManagerAgentChannel,
    AIToolsTeamManagerAgentConsumer,
)

__all__ = [
    "DefaultTeamManagerAgentProducer",
    "DefaultTeamManagerAgentChannel",
    "DefaultTeamManagerAgentConsumer",
    "AIPlanTeamManagerAgentProducer",
    "AIPlanTeamManagerAgentChannel",
    "AIPlanTeamManagerAgentConsumer",
    "AIToolsTeamManagerAgentProducer",
    "AIToolsTeamManagerAgentChannel",
    "AIToolsTeamManagerAgentConsumer",
]
