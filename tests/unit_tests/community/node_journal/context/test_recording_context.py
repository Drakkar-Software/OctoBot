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
from fastapi import HTTPException

import octobot_sync.errors as sync_errors

import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording_context as recording_context_module


class TestSchedulerInitPhase:
    def test_calls_on_failure_when_context_raises(self):
        on_failure_mock = mock.Mock()
        with pytest.raises(RuntimeError):
            with recording_context_module.scheduler_init_phase(
                init_phase=journal_enums.JournalInitPhase.DBOS_CREATE,
                backend=journal_enums.JournalSchedulerBackend.SQLITE,
                on_failure=on_failure_mock,
            ):
                raise RuntimeError("init failed")
        on_failure_mock.assert_called_once()
        assert on_failure_mock.call_args.kwargs["init_phase"] == journal_enums.JournalInitPhase.DBOS_CREATE
        assert on_failure_mock.call_args.kwargs["backend"] == journal_enums.JournalSchedulerBackend.SQLITE


class TestSyncReadOperation:
    def test_records_sync_read_failed_on_exception(self, journal_persisted_state):
        with pytest.raises(sync_errors.OctobotSyncWalletNotFoundError):
            with recording_context_module.sync_read_operation(
                resolve_collection=lambda: "user-data",
                resolve_failure_reason=lambda exc: "wallet_not_found",
            ):
                raise sync_errors.OctobotSyncWalletNotFoundError("missing")
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SYNC_READ_FAILED
        assert event_line.attributes.collection == "user-data"
        assert event_line.attributes.failure_reason == "wallet_not_found"
        assert event_line.attributes.error_category == "OctobotSyncWalletNotFoundError"


class TestSyncStorageError:
    def test_records_sync_storage_event_on_exception(self, journal_persisted_state):
        with pytest.raises(ValueError):
            with recording_context_module.sync_storage_error(
                event=journal_events.NodeJournalEvent.SYNC_STORAGE_FORMAT_ERROR,
                collection="user-strategies",
                provider=journal_enums.SyncStorageProvider.LOCAL,
            ):
                raise ValueError("invalid json")
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SYNC_STORAGE_FORMAT_ERROR
        assert event_line.attributes.collection == "user-strategies"
        assert event_line.attributes.error_category == "ValueError"


class TestRaiseWalletSetupHttpError:
    def test_records_failure_and_raises_http_exception(self, journal_persisted_state):
        with pytest.raises(HTTPException) as raised_error:
            recording_context_module.raise_wallet_setup_http_error(
                http_status=400,
                failure_reason=journal_enums.WalletSetupFailureReason.WALLET_ERROR,
                setup_method=journal_enums.WalletSetupMethod.CREATE,
                detail="bad passphrase",
                error=ValueError("bad"),
            )
        assert raised_error.value.status_code == 400
        assert raised_error.value.detail == "bad passphrase"
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.WALLET_SETUP_FAILED
        assert event_line.attributes.http_status == 400
        assert event_line.attributes.failure_reason == journal_enums.WalletSetupFailureReason.WALLET_ERROR.value
        assert event_line.attributes.error_message is None
