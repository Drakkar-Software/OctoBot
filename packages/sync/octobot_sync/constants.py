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

MAX_BODY_SIZE_META = 2 * 1024 * 1024  # 2 MB — product meta + logo upload
MAX_BODY_SIZE_SIGNAL = 64 * 1024  # 64 KB — signal payload
MAX_BODY_SIZE_PERFORMANCE = 64 * 1024  # 64 KB — live performance snapshot
MAX_BODY_SIZE_PRIVATE = 10 * 1024 * 1024  # 10 MB — private documents

HKDF_INFO_USER_DATA = "octobot-sync-user-data"
HKDF_INFO_PLATFORM_DATA = "octobot-sync-platform-data"

MAX_NONCE_LENGTH = 128
MAX_PUBKEY_LENGTH = 256
MAX_SIGNATURE_LENGTH = 512
TIMESTAMP_WINDOW_MS = 30_000

HEADER_PUBKEY = "X-OctoBot-Pubkey"
HEADER_SIGNATURE = "X-OctoBot-Signature"
HEADER_TIMESTAMP = "X-OctoBot-Timestamp"
HEADER_NONCE = "X-OctoBot-Nonce"
HEADER_CHAIN = "X-OctoBot-Chain"
HEADER_ORIGINAL_METHOD = "X-Original-Method"
HEADER_ORIGINAL_URI = "X-Original-URI"

COLLECTIONS_FILE = "collections.json"

DEFAULT_VERSION = 0
