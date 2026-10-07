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

import octobot.enums as octobot_enums

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.lifecycle as journal_lifecycle


class TestInitializeJournalDefaultDistribution:
    def test_skips_journal_init_for_non_node_distribution(self):
        config_mock = mock.Mock()
        with (
            mock.patch(
                "octobot.community.node_journal.lifecycle.configuration_manager.get_distribution",
                return_value=octobot_enums.OctoBotDistribution.DEFAULT,
            ),
            mock.patch(
                "octobot.community.node_journal.lifecycle.journal_module.initialize_for_config",
            ) as init_for_config_mock,
            mock.patch.object(
                journal_lifecycle,
                "build_existing_config_snapshot",
            ) as snapshot_mock,
        ):
            journal_lifecycle.initialize_journal(config_mock)
        init_for_config_mock.assert_not_called()
        snapshot_mock.assert_not_called()


class TestInitializeJournalNodeDistribution:
    def test_initializes_journal_and_builds_snapshot(self):
        config_mock = mock.Mock()
        snapshot = journal_lifecycle.ExistingConfigSnapshot(
            wallet_configured=False,
            account_count=0,
            reconciled=False,
        )
        with (
            mock.patch(
                "octobot.community.node_journal.lifecycle.configuration_manager.get_distribution",
                return_value=octobot_enums.OctoBotDistribution.NODE,
            ),
            mock.patch(
                "octobot.community.node_journal.lifecycle.journal_module.initialize_for_config",
            ) as init_for_config_mock,
            mock.patch.object(
                journal_lifecycle,
                "build_existing_config_snapshot",
                return_value=snapshot,
            ) as snapshot_mock,
        ):
            journal_lifecycle.initialize_journal(config_mock)
        init_for_config_mock.assert_called_once_with(config_mock)
        snapshot_mock.assert_called_once_with()


class TestRecordNodeStartupFailed:
    def test_initializes_journal_and_records_failure(self, journal_persisted_state):
        config_mock = mock.Mock()
        snapshot = journal_lifecycle.ExistingConfigSnapshot(
            wallet_configured=False,
            account_count=0,
            reconciled=False,
        )
        with (
            mock.patch.object(journal_lifecycle, "build_existing_config_snapshot", return_value=snapshot),
            mock.patch("octobot.community.node_journal.lifecycle.journal_module.initialize_for_config") as init_mock,
        ):
            journal_lifecycle.record_node_startup_failed(
                RuntimeError("startup boom"),
                startup_phase="prepare",
                force_exit=True,
                config=config_mock,
            )
        init_mock.assert_called_once_with(config_mock)
        events = journal_module.read_events()
        event_line = events[0]
        assert event_line.event == journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED
        assert event_line.attributes.startup_phase == "prepare"
        assert event_line.attributes.new_install is True
