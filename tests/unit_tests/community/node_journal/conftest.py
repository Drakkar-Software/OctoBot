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

import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.node_journal.safe as journal_safe_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store
import octobot.community.node_journal.sync_session as sync_session_module

from test_utils.journal_test_support import enabled_node_journal_environment


def reset_journal_state() -> None:
    journal_state.bind_config(None)
    journal_state._persisted_state = None
    journal_state._session_id = None


@pytest.fixture
def journal_user_root(tmp_path):
    user_root = tmp_path / "user"
    user_root.mkdir()
    return user_root


@pytest.fixture(autouse=True)
def re_enable_node_journal():
    with enabled_node_journal_environment():
        yield


@pytest.fixture(autouse=True)
def isolated_journal_environment(journal_user_root):
    journal_store.reset_default_store()
    reset_journal_state()
    sync_session_module._tracker_reset_after_startup = False
    with mock.patch.object(
        user_root_folder_provider,
        "get_user_root_folder",
        return_value=str(journal_user_root),
    ):
        yield journal_user_root
    journal_store.reset_default_store()
    reset_journal_state()
    sync_session_module._tracker_reset_after_startup = False


@pytest.fixture(autouse=True)
def surface_journal_errors(request):
    if request.node.path.name == "test_safe.py":
        yield
        return

    def run_without_swallowing(operation_name, operation, *, default):
        del operation_name, default
        return operation()

    with mock.patch.object(
        journal_safe_module,
        "run_journal_operation",
        side_effect=run_without_swallowing,
    ):
        yield


@pytest.fixture
def journal_persisted_state():
    state = journal_state.load_persisted_state()
    state.install_id = "test-install-id"
    state.onboarding_started_at = 1_000.0
    state.onboarding_complete = False
    state.first_automation_started_at = None
    state.connection_sequence = 0
    state.last_user_data_pull_at = None
    state.tracked_automation_ids = []
    journal_state.save_persisted_state(state)
    return state
