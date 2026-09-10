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

import octobot_protocol.models as protocol_models

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording


class TestRecordAccountEditSucceeded:
    def test_records_account_metadata(self, journal_persisted_state):
        journal_recording.record_account_edit_succeeded(
            account_id="acc-edit-1",
            is_simulated=True,
            exchange_name="binanceus",
            account_state=protocol_models.AccountStatus.VALID.value,
            user_action_id="ua-edit",
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNT_EDIT_SUCCEEDED.value
        assert events[0]["attributes"]["account_id"] == "acc-edit-1"
        assert events[0]["attributes"]["is_simulated"] is True
        assert events[0]["attributes"]["exchange_name"] == "binanceus"
        assert events[0]["attributes"]["account_state"] == protocol_models.AccountStatus.VALID.value
        assert events[0]["attributes"]["user_action_id"] == "ua-edit"
