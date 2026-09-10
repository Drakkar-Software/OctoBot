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

import octobot.community.node_journal.startup as journal_startup


class TestInitializeJournalDefaultDistribution:
    def test_skips_journal_init_for_non_node_distribution(self):
        config_mock = mock.Mock()
        with (
            mock.patch(
                "octobot.community.node_journal.startup.configuration_manager.get_distribution",
                return_value=octobot_enums.OctoBotDistribution.DEFAULT,
            ),
            mock.patch(
                "octobot.community.node_journal.startup.journal_module.initialize_for_config",
            ) as init_for_config_mock,
            mock.patch.object(
                journal_startup,
                "build_existing_config_snapshot",
            ) as snapshot_mock,
        ):
            journal_startup.initialize_journal(config_mock)
        init_for_config_mock.assert_not_called()
        snapshot_mock.assert_not_called()


class TestInitializeJournalNodeDistribution:
    def test_initializes_journal_and_builds_snapshot(self):
        config_mock = mock.Mock()
        snapshot = journal_startup.ExistingConfigSnapshot(
            wallet_configured=False,
            account_count=0,
            automation_count=0,
            reconciled=False,
        )
        with (
            mock.patch(
                "octobot.community.node_journal.startup.configuration_manager.get_distribution",
                return_value=octobot_enums.OctoBotDistribution.NODE,
            ),
            mock.patch(
                "octobot.community.node_journal.startup.journal_module.initialize_for_config",
            ) as init_for_config_mock,
            mock.patch.object(
                journal_startup,
                "build_existing_config_snapshot",
                return_value=snapshot,
            ) as snapshot_mock,
        ):
            journal_startup.initialize_journal(config_mock)
        init_for_config_mock.assert_called_once_with(config_mock)
        snapshot_mock.assert_called_once_with()
