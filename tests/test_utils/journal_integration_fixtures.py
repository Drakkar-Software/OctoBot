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

import contextlib

import mock
import pytest

import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.recording.sync as sync_module
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.store as journal_store

from test_utils.journal_test_support import enabled_node_journal_environment


def reset_journal_state() -> None:
    journal_state.bind_config(None)
    journal_state._persisted_state = None
    journal_state._session_id = None


def should_skip_surface_journal_errors(request) -> bool:
    node_path = request.node.path
    if node_path.name == "test_record.py" and node_path.parent.name == "pipeline":
        return True
    test_class = getattr(request.node, "cls", None)
    if test_class is not None and test_class.__name__ == "TestRunJournalStoreOperation":
        return True
    return False


@contextlib.contextmanager
def surface_journal_errors_context():
    def run_without_swallowing(operation_name, operation, *, default):
        del operation_name, default
        return operation()

    with mock.patch.object(
        journal_module,
        "run_journal_operation",
        side_effect=run_without_swallowing,
    ), mock.patch.object(
        journal_store,
        "run_journal_store_operation",
        side_effect=run_without_swallowing,
    ):
        yield


@contextlib.contextmanager
def isolated_journal_environment_context(journal_user_root_path: str):
    journal_store.reset_default_store()
    reset_journal_state()
    sync_module._tracker_reset_after_startup = False
    with mock.patch.object(
        user_root_folder_provider,
        "get_user_root_folder",
        return_value=journal_user_root_path,
    ):
        yield
    journal_store.reset_default_store()
    reset_journal_state()
    sync_module._tracker_reset_after_startup = False


@pytest.fixture
def journal_user_root(tmp_path):
    user_root = tmp_path / "user"
    user_root.mkdir()
    return user_root


@pytest.fixture
def node_journal_enabled():
    with enabled_node_journal_environment():
        yield


@pytest.fixture
def isolated_journal_environment(journal_user_root):
    with isolated_journal_environment_context(str(journal_user_root)):
        yield journal_user_root


@pytest.fixture
def surface_journal_errors(request):
    if should_skip_surface_journal_errors(request):
        yield
        return
    with surface_journal_errors_context():
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
