#  Agent seed full folder clear tests.

import pytest

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.scheduler_sqlite as agent_seed_scheduler_sqlite
import tools.agent_seed.paths as agent_seed_paths


class TestClearAgentSeedUserFolder:
    def test_clear_removes_user_folder(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        user_folder.mkdir()
        sqlite_path.write_text("db", encoding="utf-8")
        agent_seed_scheduler_sqlite.clear_agent_seed_user_folder(user_folder, sqlite_path)
        assert not user_folder.exists()
        assert not sqlite_path.exists()

    def test_clear_raises_when_never_initialized(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = tmp_path / "tasks.db"
        with pytest.raises(agent_seed_errors.AgentSeedClearNotInitializedError) as error_info:
            agent_seed_scheduler_sqlite.clear_agent_seed_user_folder(user_folder, sqlite_path)
        assert str(user_folder) in str(error_info.value)
        assert str(sqlite_path) in str(error_info.value)

    def test_clear_succeeds_with_marker_only(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        user_folder.mkdir()
        agent_seed_paths.marker_path(user_folder).write_text("1\n", encoding="utf-8")
        agent_seed_scheduler_sqlite.clear_agent_seed_user_folder(user_folder, sqlite_path)
        assert not user_folder.exists()
