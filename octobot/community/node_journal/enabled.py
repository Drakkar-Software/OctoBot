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

import os

import octobot.community.node_journal.constants as journal_constants

_DISABLED_VALUES = frozenset({"0", "false", "no", "off"})


def is_journal_enabled() -> bool:
    raw_value = os.environ.get(journal_constants.JOURNAL_ENABLED_ENV_VAR)
    if raw_value is None:
        return True
    return raw_value.strip().lower() not in _DISABLED_VALUES
