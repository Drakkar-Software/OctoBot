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

from octobot.agent import channel
from octobot.agent import team

# Base agent channel classes
from octobot.agent.channel import (
    AbstractAgentChannel,
    AbstractAgentChannelProducer,
    AbstractAgentChannelConsumer,
)

# AI agent channel classes (with LLM capabilities)
from octobot.agent.channel import (
    AbstractAIAgentChannelProducer,
    AbstractAIAgentChannelConsumer,
)

# Team channel classes
from octobot.agent.team import (
    AbstractAgentTeamChannel,
    AbstractAgentTeamChannelProducer,
    AbstractAgentTeamChannelConsumer,
    AbstractSyncAgentTeamChannelProducer,
    AbstractLiveAgentTeamChannelProducer,
)


__all__ = [
    # Base classes
    "AbstractAgentChannel",
    "AbstractAgentChannelProducer",
    "AbstractAgentChannelConsumer",
    # AI agent classes
    "AbstractAIAgentChannelProducer",
    "AbstractAIAgentChannelConsumer",
    # Team classes
    "AbstractAgentTeamChannel",
    "AbstractAgentTeamChannelProducer",
    "AbstractAgentTeamChannelConsumer",
    "AbstractSyncAgentTeamChannelProducer",
    "AbstractLiveAgentTeamChannelProducer",
]
