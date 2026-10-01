#  Agent seed full folder clear tests.

import tools.agent_seed.operations.clear as agent_seed_clear


class TestClearAgentSeedUserFolder:
    def test_clear_removes_user_folder(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        user_folder.mkdir()
        sqlite_path.write_text("db", encoding="utf-8")
        agent_seed_clear.clear_agent_seed_user_folder(user_folder, sqlite_path)
        assert not user_folder.exists()
        assert not sqlite_path.exists()
