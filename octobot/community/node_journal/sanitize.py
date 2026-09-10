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

import re

import octobot.community.node_journal.constants as journal_constants

_ETH_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
_BECH32_PATTERN = re.compile(r"\b(bc1|tb1)[a-z0-9]{25,90}\b", re.IGNORECASE)
_API_KEY_LIKE_PATTERN = re.compile(
    r"\b(?:api[_-]?key|secret|token|passphrase|password|private[_-]?key)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_HOME_PATH_PATTERN = re.compile(r"(?i)(?:/[Uu]sers/|/home/)[^\s]+")


def sanitize_error_message(raw_message: str | None) -> str:
    if not raw_message:
        return ""
    sanitized = str(raw_message)
    sanitized = _ETH_ADDRESS_PATTERN.sub("[redacted-address]", sanitized)
    sanitized = _BECH32_PATTERN.sub("[redacted-address]", sanitized)
    sanitized = _API_KEY_LIKE_PATTERN.sub("[redacted-secret]", sanitized)
    sanitized = _EMAIL_PATTERN.sub("[redacted-email]", sanitized)
    sanitized = _HOME_PATH_PATTERN.sub("[redacted-path]", sanitized)
    if len(sanitized) > journal_constants.ERROR_MESSAGE_MAX_LENGTH:
        truncated_length = journal_constants.ERROR_MESSAGE_MAX_LENGTH - 1
        sanitized = sanitized[:truncated_length] + "…"
    return sanitized
