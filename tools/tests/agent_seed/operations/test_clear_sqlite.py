#  Agent seed clear sqlite helper unit tests.

import mock
import pytest

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.operations.clear as agent_seed_clear


class TestRemoveSchedulerSqliteFiles:
    def test_missing_sqlite_files_proceeds(self, tmp_path):
        sqlite_path = tmp_path / "tasks.db"
        agent_seed_clear.remove_scheduler_sqlite_files(sqlite_path)
        assert not sqlite_path.exists()

    def test_permission_error_raises_locked_message(self, tmp_path):
        sqlite_path = tmp_path / "tasks.db"
        sqlite_path.write_text("locked", encoding="utf-8")
        with mock.patch("os.remove", side_effect=PermissionError("in use")):
            with pytest.raises(agent_seed_clear.AgentSeedClearLockedSqliteError) as error_info:
                agent_seed_clear.remove_scheduler_sqlite_files(sqlite_path)
        assert demo_agent_seed_constants.DEMO_AGENT_SEED_CLEAR_LOCKED_SQLITE_MESSAGE_PREFIX in str(
            error_info.value,
        )
