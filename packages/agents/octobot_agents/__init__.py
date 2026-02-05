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

from octobot_agents import agent
from octobot_agents.agent import (
    AbstractAgentChannel,
    AbstractAgentChannelProducer,
    AbstractAgentChannelConsumer,
    AbstractAIAgentChannel,
    AbstractAIAgentChannelProducer,
    AbstractAIAgentChannelConsumer,
    AbstractMemoryAgent,
    export_memories,
    import_memories,
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
    get_memory_tools,
    execute_memory_tool,
)

from octobot_agents import utils
from octobot_agents.utils import (
    extract_json_from_content,
    extract_json_between_braces,
    extract_json_from_markdown,
    extract_json_from_xml_tags,
    preprocess_json_content,
)

from octobot_agents import team
from octobot_agents.team import (
    AbstractAgentsTeamChannel,
    AbstractAgentsTeamChannelProducer,
    AbstractAgentsTeamChannelConsumer,
    AbstractSyncAgentsTeamChannelProducer,
    AbstractLiveAgentsTeamChannelProducer,
    AbstractCriticAgent,
    AbstractJudgeAgent,
    # Deep Agents Team
    AbstractDeepAgentsTeamChannel,
    AbstractDeepAgentsTeamChannelConsumer,
    AbstractDeepAgentsTeamChannelProducer,
)

from octobot_agents import errors
from octobot_agents.errors import (
    AgentError,
    TeamConfigurationError,
    MissingManagerError,
    MissingRequiredInputError,
    AgentConfigurationError,
    StorageError,
    UnsupportedStorageTypeError,
    DeepAgentError,
    DeepAgentNotAvailableError,
    SubagentError,
    SubagentTimeoutError,
    SupervisorError,
    DebateError,
    DebateConvergenceError,
    MemoryPathError,
    ToolExecutionError,
)

from octobot_agents import enums
from octobot_agents.enums import (
    MemoryStorageType,
    StepType,
    JudgeDecisionType,
    AgentRole,
    SubagentMode,
    ToolCallMode,
    MemoryScope,
    ExecutionStatus,
)

from octobot_agents import models
from octobot_agents.models import (
    SubagentConfig,
    MemoryEntry,
    TodoItem,
    DeepAgentResult,
    TeamExecutionResult,
    SupervisorState,
)

__all__ = [
    "AbstractAgentChannel",
    "AbstractAgentChannelProducer",
    "AbstractAgentChannelConsumer",
    "AbstractAIAgentChannel",
    "AbstractAIAgentChannelProducer",
    "AbstractAIAgentChannelConsumer",
    "AbstractAgentsTeamChannel",
    "AbstractAgentsTeamChannelProducer",
    "AbstractAgentsTeamChannelConsumer",
    "AbstractSyncAgentsTeamChannelProducer",
    "AbstractLiveAgentsTeamChannelProducer",
    "AbstractMemoryStorage",
    "JSONMemoryStorage",
    "AbstractMemoryAgent",
    "create_memory_storage",
    "export_memories",
    "import_memories",
    "get_memory_tools",
    "execute_memory_tool",
    "AbstractCriticAgent",
    "AbstractJudgeAgent",
    "AgentError",
    "TeamConfigurationError",
    "MissingManagerError",
    "MissingRequiredInputError",
    "AgentConfigurationError",
    "StorageError",
    "UnsupportedStorageTypeError",
    # Deep Agent errors
    "DeepAgentError",
    "DeepAgentNotAvailableError",
    "SubagentError",
    "SubagentTimeoutError",
    "SupervisorError",
    "DebateError",
    "DebateConvergenceError",
    "MemoryPathError",
    "ToolExecutionError",
    # Deep Agent (from agent/channels/deep_agent.py)
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
    # Utilities
    "extract_json_from_content",
    "extract_json_between_braces",
    "extract_json_from_markdown",
    "extract_json_from_xml_tags",
    "preprocess_json_content",
    # Deep Agents Team
    "AbstractDeepAgentsTeamChannel",
    "AbstractDeepAgentsTeamChannelConsumer",
    "AbstractDeepAgentsTeamChannelProducer",
    # Enums
    "MemoryStorageType",
    "StepType",
    "JudgeDecisionType",
    "AgentRole",
    "SubagentMode",
    "ToolCallMode",
    "MemoryScope",
    "ExecutionStatus",
    # Deep Agent models
    "SubagentConfig",
    "MemoryEntry",
    "TodoItem",
    "DeepAgentResult",
    "TeamExecutionResult",
    "SupervisorState",
]
