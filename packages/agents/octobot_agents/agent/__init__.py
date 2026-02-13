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

from octobot_agents.agent import channels
from octobot_agents.agent.channels import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
    AbstractAIAgentChannel,
    AbstractAIAgentChannelConsumer,
    AbstractAIAgentChannelProducer,
    # Deep Agent
    DEEP_AGENTS_AVAILABLE,
    AbstractDeepAgentChannel,
    AbstractDeepAgentChannelConsumer,
    AbstractDeepAgentChannelProducer,
    create_memory_backend,
    get_agent_memory_path,
    build_dictionary_subagent,
    build_compiled_subagent,
    build_subagents_from_agents,
    build_subagents_from_producers,
    create_deep_agent_safe,
    create_supervisor_agent,
    create_team_deep_agent,
    # Skills utilities
    load_skill_from_file,
    discover_skills,
    create_skills_files_dict,
    # HITL utilities
    create_interrupt_config,
    build_hitl_decision,
)

from octobot_agents import storage
from octobot_agents.storage import (
    AbstractMemoryStorage,
    JSONMemoryStorage,
    create_memory_storage,
)

from octobot_agents.agent import memory
from octobot_agents.agent.memory import (
    MemoryAgentMixin,
)

__all__ = [
    "AbstractAgentChannel",
    "AbstractAgentChannelConsumer",
    "AbstractAgentChannelProducer",
    "AbstractAIAgentChannel",
    "AbstractAIAgentChannelConsumer",
    "AbstractAIAgentChannelProducer",
    "AbstractMemoryStorage",
    "JSONMemoryStorage",
    "MemoryAgentMixin",
    "create_memory_storage",
    # Deep Agent
    "DEEP_AGENTS_AVAILABLE",
    "AbstractDeepAgentChannel",
    "AbstractDeepAgentChannelConsumer",
    "AbstractDeepAgentChannelProducer",
    "create_memory_backend",
    "get_agent_memory_path",
    "build_dictionary_subagent",
    "build_compiled_subagent",
    "build_subagents_from_agents",
    "build_subagents_from_producers",
    "create_deep_agent_safe",
    "create_supervisor_agent",
    "create_team_deep_agent",
    # Skills utilities
    "load_skill_from_file",
    "discover_skills",
    "create_skills_files_dict",
    # HITL utilities
    "create_interrupt_config",
    "build_hitl_decision",
]
