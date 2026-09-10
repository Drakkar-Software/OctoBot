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

import octobot_commons.configuration as configuration

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.state as journal_state


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
