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

class AgentError(Exception):
    """Base exception for all octobot_agents errors."""


class TeamConfigurationError(AgentError):
    """Raised when a team is misconfigured."""


class MissingManagerError(TeamConfigurationError):
    """Raised when a team requires a manager but none is provided."""


class MissingRequiredInputError(AgentError):
    """Raised when required input data is missing."""


class AgentConfigurationError(AgentError):
    """Raised when an agent is misconfigured."""


class StorageError(AgentError):
    """Raised when there's an error with storage operations."""


class UnsupportedStorageTypeError(StorageError):
    """Raised when an unsupported storage type is requested."""


class DeepAgentError(AgentError):
    """Base exception for Deep Agent related errors."""


class DeepAgentNotAvailableError(DeepAgentError):
    """Raised when deep_agents package is not installed."""


class SubagentError(DeepAgentError):
    """Raised when there's an error with subagent execution."""


class SubagentTimeoutError(SubagentError):
    """Raised when a subagent execution times out."""


class SupervisorError(DeepAgentError):
    """Raised when the supervisor agent encounters an error."""


class DebateError(AgentError):
    """Raised when there's an error in the debate workflow."""


class DebateConvergenceError(DebateError):
    """Raised when debate fails to converge within max rounds."""


class MemoryPathError(StorageError):
    """Raised when there's an error with memory path operations."""


class ToolExecutionError(AgentError):
    """Raised when a tool execution fails."""
