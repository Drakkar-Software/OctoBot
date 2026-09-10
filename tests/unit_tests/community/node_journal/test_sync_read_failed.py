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
from starfish_server.storage.base import StoreContext

import octobot_sync.enums as sync_enums
import octobot_sync.errors as sync_errors
import octobot_sync.server as sync_server
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module


def _user_data_context() -> StoreContext:
    return StoreContext(
        collection=sync_enums.Collections.USER_DATA.value,
        params={},
        identity="user-1",
        roles=(),
        action="read",
    )


class TestSyncReadFailureReason:
    def test_maps_wallet_not_found(self):
        assert sync_server._sync_read_failure_reason(
            sync_errors.OctobotSyncWalletNotFoundError("missing"),
        ) == "wallet_not_found"

    def test_maps_identity_missing(self):
        assert sync_server._sync_read_failure_reason(
            sync_errors.OctobotSyncIdentityMissingError("missing"),
        ) == "identity_missing"

    def test_maps_storage_error(self):
        assert sync_server._sync_read_failure_reason(
            collection_errors.CollectionStorageError("broken"),
        ) == "storage_error"

    def test_maps_unknown_errors_to_other(self):
        assert sync_server._sync_read_failure_reason(RuntimeError("boom")) == "other"


class TestSyncReadFailureCollection:
    def test_uses_context_collection_when_present(self):
        context = StoreContext(
            collection="user-accounts",
            params={},
            identity="user-1",
            roles=(),
            action="read",
        )
        assert sync_server._sync_read_failure_collection(context) == "user-accounts"

    def test_defaults_to_unknown_without_context(self):
        assert sync_server._sync_read_failure_collection(None) == "unknown"


class TestGetData:
    @pytest.mark.asyncio
    async def test_records_sync_read_failed_and_reraises(self, journal_persisted_state):
        expected_error = sync_errors.OctobotSyncWalletNotFoundError("wallet missing")
        with mock.patch(
            "octobot_sync.server.user_data_protocol.get_user_data_state",
            new_callable=mock.AsyncMock,
            side_effect=expected_error,
        ):
            with pytest.raises(sync_errors.OctobotSyncWalletNotFoundError):
                await sync_server.get_data("user-data-key", _user_data_context())

        events = journal_module.read_events()
        assert len(events) == 1
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.SYNC_READ_FAILED
        assert event_line.attributes.collection == sync_enums.Collections.USER_DATA.value
        assert event_line.attributes.failure_reason == "wallet_not_found"
        assert event_line.attributes.error_category == "OctobotSyncWalletNotFoundError"

    @pytest.mark.asyncio
    async def test_successful_user_data_pull_does_not_record_sync_read_failed(self, journal_persisted_state):
        user_data_state = mock.Mock()
        user_data_state.to_json.return_value = "{}"
        with mock.patch(
            "octobot_sync.server.user_data_protocol.get_user_data_state",
            new_callable=mock.AsyncMock,
            return_value=user_data_state,
        ), mock.patch(
            "octobot_sync.server._encrypt",
            return_value="encrypted",
        ), mock.patch(
            "octobot_sync.server.node_journal.on_user_data_pull_succeeded",
        ):
            result = await sync_server.get_data("user-data-key", _user_data_context())

        assert result is not None
        sync_read_failures = [
            event_line
            for event_line in journal_module.read_events()
            if event_line.event == journal_events.NodeJournalEvent.SYNC_READ_FAILED
        ]
        assert sync_read_failures == []
