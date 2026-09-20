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

import typing

import octobot.community.node_journal as node_journal
import octobot.community.node_journal.events as journal_events


def get_wallet_setup_succeeded_timestamp() -> typing.Optional[float]:
    """Return the earliest wallet_setup_succeeded journal timestamp, if any."""
    timestamps: list[float] = []
    for event in node_journal.read_events():
        if event.event == journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED.value:
            timestamps.append(event.timestamp)
    if not timestamps:
        return None
    return min(timestamps)
