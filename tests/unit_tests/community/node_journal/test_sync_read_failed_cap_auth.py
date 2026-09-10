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
from starfish_server.router.cap_resolver import CapAuthError

import octobot_sync.app as sync_app

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module


class TestBuildRoleResolverCapAuth:
    @pytest.mark.asyncio
    async def test_records_sync_read_failed_when_cap_auth_raises(self, journal_persisted_state):
        auth_error = CapAuthError(401, "invalid cap")
        inner_resolver = mock.AsyncMock(side_effect=auth_error)
        with mock.patch("octobot_sync.app.create_cap_cert_role_resolver", return_value=inner_resolver):
            gated_resolver = sync_app._build_role_resolver(lambda _identity: True)
        with pytest.raises(CapAuthError):
            await gated_resolver(mock.Mock())
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0]["event"] == journal_events.NodeJournalEvent.SYNC_READ_FAILED.value
        assert events[0]["attributes"]["collection"] == "user-data"
        assert events[0]["attributes"]["failure_reason"] == "cap_auth"
        assert events[0]["attributes"]["error_category"] == "CapAuthError"

    @pytest.mark.asyncio
    async def test_records_sync_read_failed_when_identity_not_allowed(self, journal_persisted_state):
        auth_result = mock.Mock()
        auth_result.identity = "blocked-user"
        inner_resolver = mock.AsyncMock(return_value=auth_result)
        with mock.patch("octobot_sync.app.create_cap_cert_role_resolver", return_value=inner_resolver):
            gated_resolver = sync_app._build_role_resolver(lambda identity: identity == "allowed-user")
        with pytest.raises(CapAuthError, match="user not allowed"):
            await gated_resolver(mock.Mock())
        events = journal_module.read_events()
        assert len(events) == 1
        assert events[0]["attributes"]["failure_reason"] == "cap_auth"
