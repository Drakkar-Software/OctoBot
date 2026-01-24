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
