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
    pass


class TeamConfigurationError(AgentError):
    """Raised when a team is misconfigured."""
    pass


class MissingManagerError(TeamConfigurationError):
    """Raised when a team requires a manager but none is provided."""
    pass


class MissingRequiredInputError(AgentError):
    """Raised when required input data is missing."""
    pass


class AgentConfigurationError(AgentError):
    """Raised when an agent is misconfigured."""
    pass


class StorageError(AgentError):
    """Raised when there's an error with storage operations."""
    pass


class UnsupportedStorageTypeError(StorageError):
    """Raised when an unsupported storage type is requested."""
    pass


class DeepAgentError(AgentError):
    """Base exception for Deep Agent related errors."""
    pass


class DeepAgentNotAvailableError(DeepAgentError):
    """Raised when deep_agents package is not installed."""
    pass


class SubagentError(DeepAgentError):
    """Raised when there's an error with subagent execution."""
    pass


class SubagentTimeoutError(SubagentError):
    """Raised when a subagent execution times out."""
    pass


class SupervisorError(DeepAgentError):
    """Raised when the supervisor agent encounters an error."""
    pass


class DebateError(AgentError):
    """Raised when there's an error in the debate workflow."""
    pass


class DebateConvergenceError(DebateError):
    """Raised when debate fails to converge within max rounds."""
    pass


class MemoryPathError(StorageError):
    """Raised when there's an error with memory path operations."""
    pass


class ToolExecutionError(AgentError):
    """Raised when a tool execution fails."""
    pass
