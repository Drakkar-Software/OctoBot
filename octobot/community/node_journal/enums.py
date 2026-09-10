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


class JournalInitPhase(enum.StrEnum):
    DBOS_CREATE = "dbos_create"
    REGISTER_WORKFLOWS = "register_workflows"
    VERSION_MIGRATION = "version_migration"
    DBOS_LAUNCH = "dbos_launch"
    REGISTER_SCHEDULES = "register_schedules"


class JournalStartupPhase(enum.StrEnum):
    NODE_API_START = "node_api_start"
    BOT_INITIALIZE = "bot_initialize"
    CLI_START = "cli_start"


class JournalSchedulerBackend(enum.StrEnum):
    POSTGRES = "postgres"
    SQLITE = "sqlite"


class WalletSetupFailureReason(enum.StrEnum):
    SERVICE_UNAVAILABLE = "service_unavailable"
    ALREADY_CONFIGURED = "already_configured"
    CONCURRENT_RACE = "concurrent_race"
    WALLET_ERROR = "wallet_error"


class WalletSetupMethod(enum.StrEnum):
    CREATE = "create"
    IMPORT = "import"


class WalletOperation(enum.StrEnum):
    IMPORT = "import"
    CREATE = "create"
    DECRYPT = "decrypt"
    LOOKUP = "lookup"
    DELETE = "delete"
    RENAME = "rename"


class SyncReadFailureReason(enum.StrEnum):
    CAP_AUTH = "cap_auth"
    WALLET_NOT_FOUND = "wallet_not_found"
    IDENTITY_MISSING = "identity_missing"
    STORAGE_ERROR = "storage_error"
    OTHER = "other"


class SyncStorageRecoveryAction(enum.StrEnum):
    DROP_INVALID_ITEMS = "drop_invalid_items"
    SANITIZE_STATE = "sanitize_state"
    SKIP_ITEM = "skip_item"
    REBUILD_ITEM = "rebuild_item"
    FALLBACK_ITEM = "fallback_item"


class SyncStorageProvider(enum.StrEnum):
    LOCAL = "local"


class ConfigurationType(enum.StrEnum):
    GENERIC_PROCESS = "generic_process"
    MARKET_MAKING = "market_making"
    COPY = "copy"
    SIGNAL_BOT = "signal_bot"
    GENERIC_WORKFLOW = "generic_workflow"
    TRADING_TENTACLES = "trading_tentacles"


class OctobotKind(enum.StrEnum):
    MANUAL = "manual"
    MARKET_MAKING = "market_making"
    FLOW = "flow"


class FlowSubtype(enum.StrEnum):
    COPY = "copy"
    SIGNAL_BOT = "signal_bot"
    AI_AGENTS = "ai_agents"
    OTHER = "other"
