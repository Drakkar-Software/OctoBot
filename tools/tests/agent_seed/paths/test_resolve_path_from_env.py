#  Agent seed paths unit tests.

import tools.agent_seed.paths as agent_seed_paths


class TestDefaultOctobotRepoRoot:
    def test_points_at_octobot_repo_root(self):
        repo_root = agent_seed_paths.default_octobot_repo_root()
        assert (repo_root / "start.py").is_file()


class TestResolvePathFromEnv:
    def test_none_returns_none(self, tmp_path):
        assert agent_seed_paths.resolve_path_from_env(None, tmp_path) is None

    def test_absolute_path_unchanged(self, tmp_path):
        absolute = tmp_path / "user" / "agent-seed"
        assert agent_seed_paths.resolve_path_from_env(str(absolute), tmp_path) == absolute

    def test_relative_path_resolved_against_repo_root(self, tmp_path):
        resolved = agent_seed_paths.resolve_path_from_env("user/agent-seed", tmp_path)
        assert resolved == (tmp_path / "user" / "agent-seed").resolve()


class TestMarkerPath:
    def test_joins_marker_filename(self, tmp_path):
        user_folder = tmp_path / "agent-seed-user"
        assert agent_seed_paths.marker_path(user_folder) == (
            user_folder / agent_seed_paths.AGENT_SEED_VERSION_MARKER_FILE
        )
