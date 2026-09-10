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

JOURNAL_MAX_EVENTS = 50_000
SYNC_SESSION_GAP_SECONDS = 14_400
ERROR_MESSAGE_MAX_LENGTH = 512
JOURNAL_DIR_NAME = "node_journal"
EVENTS_FILE_NAME = "events.jsonl"
ONBOARDING_SEGMENT_FILE_NAME = "onboarding_segment.jsonl"
CONFIG_JOURNAL_SECTION = "journal"
CONFIG_INSTALL_ID = "install_id"
CONFIG_ONBOARDING_STARTED_AT = "onboarding_started_at"
CONFIG_FIRST_AUTOMATION_STARTED_AT = "first_automation_started_at"
CONFIG_CONNECTION_SEQUENCE = "connection_sequence"
CONFIG_LAST_USER_DATA_PULL_AT = "last_user_data_pull_at"
CONFIG_TRACKED_AUTOMATION_IDS = "tracked_automation_ids"
DISTRIBUTION_NODE = "node"
JOURNAL_ENABLED_ENV_VAR = "OCTOBOT_NODE_JOURNAL_ENABLED"
