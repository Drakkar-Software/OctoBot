#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

MAX_BODY_SIZE_SIGNAL = 64 * 1024  # 64 KB — signal payload
MAX_BODY_SIZE_PERFORMANCE = 64 * 1024  # 64 KB — live performance snapshot
MAX_BODY_SIZE_PRIVATE = 10 * 1024 * 1024  # 10 MB — private documents

HKDF_INFO_USER_DATA = "octobot-sync-user-data"
HKDF_SALT_STRING = "octobot-starfish-identity-v1"

BLOB_IV_KEY = "iv"
BLOB_DATA_KEY = "data"

IV_BYTES = 12

DEFAULT_ENCRYPTION_INFO = "starfish-e2e"
COLLECTIONS_FILE = "collections.json"
SYNC_NAMESPACE = "octobot"
SYNC_MOUNT_PATH = "sync"
STARFISH_SERVER_MAJOR_VERSION = "v1"

# App-specific bootstrap challenge: the EVM wallet signs this (EIP-191 personal_sign)
# to derive its Starfish (Ed25519/X25519) identity. Namespacing the challenge to
# OctoBot means the derived user_id is OctoBot-specific. MUST stay fixed forever —
# changing it changes every user's derived identity — and MUST be identical on the
# client (cap provider) and server (allowlist + bridge wallet resolver).
SYNC_BOOTSTRAP_CHALLENGE = "octobot:sync-bootstrap"

EXCHANGE_ACCOUNTS_STATE_VERSION = "1.0.0"
USER_ACCOUNTS_AUTH_STATE_VERSION = "1.0.0"
USER_ACCOUNTS_TRADING_STATE_VERSION = "1.0.0"
USER_STRATEGIES_STATE_VERSION = "1.0.0"
USER_DATA_STATE_VERSION = "1.0.0"
USER_ACTIONS_STATE_VERSION = "1.0.0"
DEBUG_STATE_VERSION = "1.0.0"
