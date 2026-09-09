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

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module


class TestIsJournalEnabled:
    def test_enabled_by_default_when_env_unset(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            assert journal_module.is_journal_enabled() is True

    def test_disabled_for_false_values(self):
        for disabled_value in ("0", "false", "no", "off", "FALSE"):
            with mock.patch.dict(
                "os.environ",
                {journal_constants.JOURNAL_ENABLED_ENV_VAR: disabled_value},
            ):
                assert journal_module.is_journal_enabled() is False


class TestRecordWhenJournalDisabled:
    def test_record_writes_nothing_and_returns_stub(self, journal_persisted_state):
        with mock.patch.dict(
            "os.environ",
            {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"},
        ):
            event_line = journal_module.record(
                journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
                attributes={"configured": True},
            )
            assert event_line.recorded is False
            assert journal_module.read_events() == []
