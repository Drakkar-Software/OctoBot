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

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording as journal_recording


class TestRecordAutomationStopped:
    def test_records_stop_attributes(self, journal_persisted_state):
        journal_recording.record_automation_stopped(
            automation_id="auto-stop-1",
            cancel_orders=True,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.AUTOMATION_STOPPED
        assert event_line.attributes.automation_id == "auto-stop-1"
        assert event_line.attributes.cancel_orders is True


class TestRecordAutomationRestarted:
    def test_records_restart_attributes(self, journal_persisted_state):
        journal_recording.record_automation_restarted(
            automation_id="auto-restart-1",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.AUTOMATION_RESTARTED
        assert event_line.attributes.automation_id == "auto-restart-1"


class TestRecordAutomationEditSucceeded:
    def test_records_edit_attributes(self, journal_persisted_state):
        journal_recording.record_automation_edit_succeeded(
            automation_id="auto-edit-1",
            octobot_kind="flow",
            flow_subtype="copy",
            user_action_id="ua-edit",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.AUTOMATION_EDIT_SUCCEEDED
        assert event_line.attributes.automation_id == "auto-edit-1"
        assert event_line.attributes.octobot_kind == "flow"
        assert event_line.attributes.flow_subtype == "copy"
        assert event_line.attributes.user_action_id == "ua-edit"


class TestRecordAccountDeleted:
    def test_records_deleted_account_metadata(self, journal_persisted_state):
        journal_recording.record_account_deleted(
            account_id="acc-deleted-1",
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNT_DELETED
        assert event_line.attributes.account_id == "acc-deleted-1"


class TestRecordAccountAuthDeleted:
    def test_records_exchange_name(self, journal_persisted_state):
        journal_recording.record_account_auth_deleted(exchange_name="binanceus")
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNT_AUTH_DELETED
        assert event_line.attributes.exchange_name == "binanceus"


class TestRecordAccountsRefreshed:
    def test_records_refresh_counts(self, journal_persisted_state):
        journal_recording.record_accounts_refreshed(
            account_ids=["acc-1", "acc-2"],
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.ACCOUNTS_REFRESHED
        assert event_line.attributes.account_ids == ["acc-1", "acc-2"]
