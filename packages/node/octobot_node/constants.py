#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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
import os

try:
    import octobot.constants as octobot_constants
    BASE_LOGS_FOLDER = octobot_constants.LOGS_FOLDER
except ImportError:
    BASE_LOGS_FOLDER = "logs"

AUTOMATION_LOGS_FOLDER = f"{BASE_LOGS_FOLDER}/automations"
PARENT_WORKFLOW_ID_LENGTH = 36 # length of a UUID4

# default to 10 retry after 1, 2, 4, 8, 16, ... 1024 seconds (total of 2047 seconds)
AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS = float(os.getenv("AUTOMATION_WORKFLOW_RETRY_INTERVAL_SECONDS", 1.0))
AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES = int(os.getenv("AUTOMATION_WORKFLOW_MAX_ITERATION_RETRIES", 10))
AUTOMATION_WORKFLOW_BACKOFF_RATE = float(os.getenv("AUTOMATION_WORKFLOW_BACKOFF_RATE", 2))

# default to 6 retries after 2, 4, 8, 16, ... 64 seconds (total of 126 seconds)
USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS = float(os.getenv("USER_ACTION_WORKFLOW_RETRY_INTERVAL_SECONDS", 2))
USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES = int(os.getenv("USER_ACTION_WORKFLOW_MAX_ITERATION_RETRIES", 6))
USER_ACTION_WORKFLOW_BACKOFF_RATE = float(os.getenv("USER_ACTION_WORKFLOW_BACKOFF_RATE", 2))

TASKS_ENCRYPTION_ENV_VARS = [
    "TASKS_SERVER_RSA_PRIVATE_KEY",
    "TASKS_SERVER_ECDSA_PRIVATE_KEY",
]

FAILURE_ERROR_DETAILS_MAX_LENGTH = 8_000

EXCHANGE_ACCOUNTS_STATE_VERSION = "1.0.0"
USER_STRATEGIES_STATE_VERSION = "1.0.0"
USER_DATA_STATE_VERSION = "1.0.0"
USER_ACTIONS_STATE_VERSION = "1.0.0"
