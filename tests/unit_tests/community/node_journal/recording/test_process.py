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

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.lifecycle as journal_lifecycle
import octobot.community.node_journal.recording as journal_recording


class TestRecordExistingConfigDetected:
    def test_records_existing_config_snapshot(self, journal_persisted_state):
        journal_recording.record_existing_config_detected(
            wallet_configured=True,
            account_count=2,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.EXISTING_CONFIG_DETECTED
        assert event_line.attributes.wallet_configured is True
        assert event_line.attributes.account_count == 2


class TestRecordReconcileCompleted:
    def test_records_automation_counts(self, journal_persisted_state):
        journal_recording.record_reconcile_completed(
            automation_count=3,
            running_automation_count=1,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.RECONCILE_COMPLETED
        assert event_line.attributes.automation_count == 3
        assert event_line.attributes.running_automation_count == 1


class TestCompleteReconcileAutomations:
    @pytest.mark.asyncio
    async def test_records_reconcile_completed_for_existing_config(self, journal_persisted_state):
        snapshot = journal_lifecycle.ExistingConfigSnapshot(
            wallet_configured=True,
            account_count=1,
            reconciled=True,
        )
        automation_states = [
            protocol_models.AutomationState(
                id="auto-1",
                status=protocol_models.WorkflowStatus.PENDING,
                metadata=protocol_models.AutomationMetadata(name="auto-1", description=""),
            ),
            protocol_models.AutomationState(
                id="auto-2",
                status=protocol_models.WorkflowStatus.RUNNING,
                metadata=protocol_models.AutomationMetadata(name="auto-2", description=""),
            ),
        ]
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["wallet-1"]
        journal_lifecycle._reconcile_completed = False
        with (
            mock.patch.object(journal_lifecycle, "build_existing_config_snapshot", return_value=snapshot),
            mock.patch("octobot_node.scheduler.is_initialized", return_value=True),
            mock.patch(
                "octobot_sync.sync.collection_providers.AccountProvider.instance",
                return_value=account_provider_mock,
            ),
            mock.patch(
                "octobot_node.scheduler.automations.automation_states_loader.load_protocol_automation_states",
                new_callable=mock.AsyncMock,
                return_value=automation_states,
            ),
        ):
            await journal_lifecycle.complete_reconcile_automations()
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.RECONCILE_COMPLETED
        assert event_line.attributes.automation_count == 2
        assert event_line.attributes.running_automation_count == 1


class TestRecordSchedulerInitFailed:
    def test_records_init_phase_and_backend(self, journal_persisted_state):
        journal_recording.record_scheduler_init_failed(
            init_phase="dbos_create",
            backend="sqlite",
            error=RuntimeError("dbos unavailable"),
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SCHEDULER_INIT_FAILED
        assert event_line.attributes.init_phase == "dbos_create"
        assert event_line.attributes.backend == "sqlite"
        assert event_line.attributes.error_category == "RuntimeError"


class TestRecordProcessStartupFailed:
    def test_records_startup_failure_metadata(self, journal_persisted_state):
        journal_recording.record_process_startup_failed(
            startup_phase="node_api_start",
            error=RuntimeError("api failed"),
            force_exit=False,
            wallet_configured=True,
            new_install=False,
            reconciled=True,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED
        assert event_line.attributes.startup_phase == "node_api_start"
        assert event_line.attributes.force_exit is False
        assert event_line.attributes.wallet_configured is True
        assert event_line.attributes.error_category == "RuntimeError"


class TestRecordProcessStartupSucceeded:
    def test_resets_sync_tracker_and_records_startup(self, journal_persisted_state):
        with mock.patch(
            "octobot.community.node_journal.recording.sync.reset_sync_tracker_after_node_startup",
        ) as reset_tracker_mock:
            journal_recording.record_process_startup_succeeded(
                wallet_configured=False,
                new_install=True,
                reconciled=False,
            )
        reset_tracker_mock.assert_called_once_with()
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED
        assert event_line.attributes.wallet_configured is False
        assert event_line.attributes.new_install is True
        assert event_line.attributes.reconciled is False
