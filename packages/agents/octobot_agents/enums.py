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
import enum


class MemoryStorageType(enum.Enum):
    """Enum for memory storage types."""
    JSON = "json"


class StepType(enum.Enum):
    """Enum for execution step type (agent vs debate)."""
    AGENT = "agent"
    DEBATE = "debate"


class JudgeDecisionType(enum.Enum):
    """Enum for judge decision in a debate step (continue or exit)."""
    CONTINUE = "continue"
    EXIT = "exit"


class AgentRole(enum.Enum):
    """Role of an agent in a team."""
    MANAGER = "manager"           # Orchestrates other agents
    WORKER = "worker"             # Performs specialized tasks
    CRITIC = "critic"             # Critiques and validates
    JUDGE = "judge"               # Makes final decisions in debates
    MEMORY = "memory"             # Manages long-term memory


class SubagentMode(enum.Enum):
    """Mode of subagent execution."""
    SEQUENTIAL = "sequential"     # Execute one at a time
    PARALLEL = "parallel"         # Execute concurrently
    DAG = "dag"                   # Execute following dependency graph


class ToolCallMode(enum.Enum):
    """How tool calls are handled."""
    SYNC = "sync"                 # Wait for result
    ASYNC = "async"               # Fire and forget
    STREAMING = "streaming"       # Stream results


class MemoryScope(enum.Enum):
    """Scope of memory storage."""
    AGENT = "agent"               # Private to single agent
    TEAM = "team"                 # Shared within team
    GLOBAL = "global"             # Shared across all agents


class ExecutionStatus(enum.Enum):
    """Status of agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
