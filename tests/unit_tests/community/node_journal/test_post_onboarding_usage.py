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
        assert events[0]["event"] == journal_events.NodeJournalEvent.AUTOMATION_STOPPED.value
        assert events[0]["attributes"]["automation_id"] == "auto-stop-1"
        assert events[0]["attributes"]["cancel_orders"] is True


class TestRecordAutomationRestarted:
    def test_records_restart_attributes(self, journal_persisted_state):
        journal_recording.record_automation_restarted(
            automation_id="auto-restart-1",
            automation_count=3,
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.AUTOMATION_RESTARTED.value
        assert events[0]["attributes"]["automation_id"] == "auto-restart-1"
        assert events[0]["attributes"]["automation_count"] == 3


class TestRecordAutomationEditSucceeded:
    def test_records_edit_attributes(self, journal_persisted_state):
        journal_recording.record_automation_edit_succeeded(
            automation_id="auto-edit-1",
            octobot_kind="flow",
            flow_subtype="copy",
            user_action_id="ua-edit",
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.AUTOMATION_EDIT_SUCCEEDED.value
        assert events[0]["attributes"]["automation_id"] == "auto-edit-1"
        assert events[0]["attributes"]["octobot_kind"] == "flow"
        assert events[0]["attributes"]["flow_subtype"] == "copy"
        assert events[0]["attributes"]["user_action_id"] == "ua-edit"


class TestRecordAccountDeleted:
    def test_records_deleted_account_metadata(self, journal_persisted_state):
        journal_recording.record_account_deleted(
            is_simulated=False,
            exchange_name="kraken",
            account_count=1,
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNT_DELETED.value
        assert events[0]["attributes"]["account_count"] == 1


class TestRecordAccountAuthDeleted:
    def test_records_exchange_name(self, journal_persisted_state):
        journal_recording.record_account_auth_deleted(exchange_name="binanceus")
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNT_AUTH_DELETED.value
        assert events[0]["attributes"]["exchange_name"] == "binanceus"


class TestRecordAccountsRefreshed:
    def test_records_refresh_counts(self, journal_persisted_state):
        journal_recording.record_accounts_refreshed(
            account_count=4,
            refreshed_count=2,
        )
        events = journal_module.read_events()
        assert events[0]["event"] == journal_events.NodeJournalEvent.ACCOUNTS_REFRESHED.value
        assert events[0]["attributes"]["account_count"] == 4
        assert events[0]["attributes"]["refreshed_count"] == 2
