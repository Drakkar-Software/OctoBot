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
import os
import pytest

import octobot_commons.configuration as configuration

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.state as journal_state

_MANIFEST = journal_enums.JournalManifestField


class TestMarkFirstAutomationStarted:
    def test_persists_to_bound_config(self):
        config_mock = mock.Mock(spec=configuration.Configuration)
        config_mock.config = {
            journal_constants.CONFIG_JOURNAL_SECTION: {
                journal_constants.CONFIG_INSTALL_ID: "install-1",
                journal_constants.CONFIG_ONBOARDING_STARTED_AT: 1_000.0,
            },
        }
        journal_state.bind_config(config_mock)
        journal_state._persisted_state = None
        journal_state.mark_first_automation_started(500.0)
        journal_section = config_mock.config[journal_constants.CONFIG_JOURNAL_SECTION]
        assert journal_section[journal_constants.CONFIG_FIRST_AUTOMATION_STARTED_AT] == 500.0
        config_mock.save.assert_called()
        journal_state._persisted_state = None
        reloaded_state = journal_state.load_persisted_state(config_mock)
        assert reloaded_state.first_automation_started_at == 500.0
        assert reloaded_state.onboarding_complete is True


class TestJournalDirectory:
    def test_uses_user_node_journal_path(self, tmp_path):
        user_root = tmp_path / "user"
        user_root.mkdir(exist_ok=True)
        with mock.patch.object(
            journal_state.user_root_folder_provider,
            "get_user_root_folder",
            return_value=str(user_root),
        ):
            journal_directory = journal_state.get_journal_directory()
        assert journal_directory == str(user_root / journal_constants.JOURNAL_DIR_NAME)


class TestEnsureJournalManifest:
    def test_creates_manifest_with_install_id(self, journal_persisted_state):
        journal_directory = journal_state.get_journal_directory()
        manifest_path = os.path.join(journal_directory, journal_constants.MANIFEST_FILE_NAME)
        if os.path.isfile(manifest_path):
            os.remove(manifest_path)
        manifest = journal_state.ensure_journal_manifest(journal_directory)
        assert manifest[_MANIFEST.SCHEMA.value] == journal_constants.JOURNAL_SCHEMA_VERSION
        assert manifest[_MANIFEST.INSTALL_ID.value] == journal_persisted_state.install_id
