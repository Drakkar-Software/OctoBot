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
    JSON = "json"


class StepType(enum.Enum):
    AGENT = "agent"
    DEBATE = "debate"


class JudgeDecisionType(enum.Enum):
    CONTINUE = "continue"
    EXIT = "exit"


class AgentRole(enum.Enum):
    MANAGER = "manager"           # Orchestrates other agents
    WORKER = "worker"             # Performs specialized tasks
    CRITIC = "critic"             # Critiques and validates
    JUDGE = "judge"               # Makes final decisions in debates
    MEMORY = "memory"             # Manages long-term memory


class SubagentMode(enum.Enum):
    SEQUENTIAL = "sequential"     # Execute one at a time
    PARALLEL = "parallel"         # Execute concurrently
    DAG = "dag"                   # Execute following dependency graph


class ToolCallMode(enum.Enum):
    SYNC = "sync"                 # Wait for result
    ASYNC = "async"               # Fire and forget
    STREAMING = "streaming"       # Stream results


class MemoryScope(enum.Enum):
    AGENT = "agent"               # Private to single agent
    TEAM = "team"                 # Shared within team
    GLOBAL = "global"             # Shared across all agents


class ExecutionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
