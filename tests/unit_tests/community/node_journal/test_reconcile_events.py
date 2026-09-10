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
import octobot.community.node_journal.recording as journal_recording
import octobot.community.node_journal.startup as journal_startup


class TestRecordExistingConfigDetected:
    def test_records_existing_config_snapshot(self, journal_persisted_state):
        journal_recording.record_existing_config_detected(
            wallet_configured=True,
            account_count=2,
            automation_count=0,
        )
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.EXISTING_CONFIG_DETECTED
        assert event_line.attributes.wallet_configured is True
        assert event_line.attributes.account_count == 2


class TestRecordReconcileCompleted:
    def test_records_automation_count(self, journal_persisted_state):
        journal_recording.record_reconcile_completed(automation_count=3)
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.RECONCILE_COMPLETED
        assert event_line.attributes.automation_count == 3


class TestCompleteReconcileAutomations:
    @pytest.mark.asyncio
    async def test_records_reconcile_completed_for_existing_config(self, journal_persisted_state):
        snapshot = journal_startup.ExistingConfigSnapshot(
            wallet_configured=True,
            account_count=1,
            automation_count=0,
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
                status=protocol_models.WorkflowStatus.PENDING,
                metadata=protocol_models.AutomationMetadata(name="auto-2", description=""),
            ),
        ]
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["wallet-1"]
        journal_startup._reconcile_completed = False
        with (
            mock.patch.object(journal_startup, "build_existing_config_snapshot", return_value=snapshot),
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
            await journal_startup.complete_reconcile_automations()
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.RECONCILE_COMPLETED
        assert event_line.attributes.automation_count == 2
