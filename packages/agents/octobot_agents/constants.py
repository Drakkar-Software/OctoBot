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

AGENT_NAME_KEY = "agent_name"
AGENT_ID_KEY = "agent_id"
TEAM_NAME_KEY = "team_name"
TEAM_ID_KEY = "team_id"
RESULT_KEY = "result"

# Agent defaults
AGENT_DEFAULT_VERSION = "1.0.0"
AGENT_DEFAULT_MAX_TOKENS: int = 10000
AGENT_DEFAULT_TEMPERATURE: float = 0.3
AGENT_DEFAULT_MAX_RETRIES: int = 3

# Memory keys
MEMORY_USER_ID_KEY = "user_id"
MEMORY_AGENT_ID_KEY = "agent_id"

# Memory operations
MEMORY_OPERATION_GENERATE = "generate"
MEMORY_OPERATION_MERGE = "merge"
MEMORY_OPERATION_UPDATE = "update"
MEMORY_OPERATION_REMOVE = "remove"
MEMORY_OPERATION_GROUP = "group"

# Memory defaults
DEFAULT_CATEGORY = "general"
DEFAULT_IMPORTANCE_SCORE = 0.5
DEFAULT_CONFIDENCE_SCORE = 0.5
DEFAULT_MAX_MEMORIES = 100

# Memory length limits
MEMORY_TITLE_MAX_LENGTH = 100
MEMORY_CONTEXT_MAX_LENGTH = 200
MEMORY_CONTENT_MAX_LENGTH = 500

# Storage constants
MEMORY_FOLDER_NAME = "agents"
MEMORY_FILE_EXTENSION = ".json"

# Team modification constants
MODIFICATION_ADDITIONAL_INSTRUCTIONS = "additional_instructions"
MODIFICATION_CUSTOM_PROMPT = "custom_prompt"
MODIFICATION_EXECUTION_HINTS = "execution_hints"

# Critic analysis types
ANALYSIS_TYPE_ISSUES = "issues"
ANALYSIS_TYPE_IMPROVEMENTS = "improvements"
ANALYSIS_TYPE_ERRORS = "errors"
ANALYSIS_TYPE_INCONSISTENCIES = "inconsistencies"
ANALYSIS_TYPE_OPTIMIZATIONS = "optimizations"

# Manager tool names
TOOL_RUN_AGENT = "run_agent"
TOOL_RUN_DEBATE = "run_debate"
TOOL_FINISH = "finish"

# Deep Agent memory paths - using /memories/ prefix for persistent storage
MEMORIES_PATH_PREFIX = "/memories/"
MEMORIES_AGENT_DATA = "data"
MEMORIES_AGENT_CONTEXT = "context"
MEMORIES_AGENT_HISTORY = "history"
MEMORIES_TEAM_SHARED = "shared"

# Deep Agent supervisor defaults
SUPERVISOR_MAX_DELEGATION_DEPTH = 3
SUPERVISOR_WORKER_TIMEOUT_SECONDS = 60

# Subagent configuration keys
SUBAGENT_NAME_KEY = "name"
SUBAGENT_INSTRUCTIONS_KEY = "instructions"
SUBAGENT_TOOLS_KEY = "tools"
SUBAGENT_MODEL_KEY = "model"
SUBAGENT_HANDOFF_BACK_KEY = "handoff_back"

# Debate workflow constants
DEBATE_MAX_ROUNDS = 3
DEBATE_CONVERGENCE_THRESHOLD = 0.8
DEBATE_MIN_CONFIDENCE = 0.6

# Human-in-the-loop (HITL) constants
HITL_DECISION_APPROVE = "approve"
HITL_DECISION_EDIT = "edit"
HITL_DECISION_REJECT = "reject"
HITL_ALLOWED_DECISIONS = [HITL_DECISION_APPROVE, HITL_DECISION_EDIT, HITL_DECISION_REJECT]
HITL_DEFAULT_ALLOWED = [HITL_DECISION_APPROVE, HITL_DECISION_REJECT]
HITL_INTERRUPT_KEY = "__interrupt__"

# Skills configuration
SKILLS_PATH_PREFIX = "/skills/"
SKILLS_MANIFEST_FILE = "SKILL.md"
SKILLS_DEFAULT_DIR = "./skills/"

# CompiledSubAgent types
COMPILED_SUBAGENT_TYPE = "compiled"
DICTIONARY_SUBAGENT_TYPE = "dictionary"
