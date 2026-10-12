#  Unit tests for stop-node and start-background CLI handlers.

import tools.agent_seed.cli as agent_seed_cli
import tools.agent_seed.operations.node_lifecycle as agent_seed_node_lifecycle


def test_stop_node_subcommand_invokes_operation(tmp_path, monkeypatch):
    calls = []

    def fake_stop_recorded_node(**kwargs):
        calls.append(kwargs)
        return "stopped ok"

    monkeypatch.setattr(
        agent_seed_node_lifecycle,
        "stop_recorded_node",
        fake_stop_recorded_node,
    )
    monkeypatch.setenv("OCTOBOT_AGENT_SEED_USER_FOLDER", str(tmp_path))
    assert agent_seed_cli.main(["stop-node", "--base-url", "http://127.0.0.1:9000"]) == 0
    assert calls[0]["base_url"] == "http://127.0.0.1:9000"
    assert calls[0]["user_folder"] == tmp_path.resolve()
    assert (
        calls[0]["stop_timeout_seconds"]
        == agent_seed_node_lifecycle.DEFAULT_STOP_TIMEOUT_SECONDS
    )


def test_stop_node_forwards_stop_timeout(tmp_path, monkeypatch):
    calls = []

    def fake_stop_recorded_node(**kwargs):
        calls.append(kwargs)
        return "stopped ok"

    monkeypatch.setattr(
        agent_seed_node_lifecycle,
        "stop_recorded_node",
        fake_stop_recorded_node,
    )
    monkeypatch.setenv("OCTOBOT_AGENT_SEED_USER_FOLDER", str(tmp_path))
    assert (
        agent_seed_cli.main(
            [
                "stop-node",
                "--base-url",
                "http://127.0.0.1:8000",
                "--stop-timeout",
                "5",
            ],
        )
        == 0
    )
    assert calls[0]["stop_timeout_seconds"] == 5.0


def test_start_background_subcommand_invokes_operation(tmp_path, monkeypatch):
    calls = []

    def fake_start_node_background(**kwargs):
        calls.append(kwargs)
        return "started ok"

    monkeypatch.setattr(
        agent_seed_node_lifecycle,
        "start_node_background",
        fake_start_node_background,
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    assert (
        agent_seed_cli.main(
            [
                "start-background",
                "--user-folder",
                str(tmp_path / "user"),
                "--base-url",
                "http://127.0.0.1:8000",
                "--repo-root",
                str(repo_root),
            ],
        )
        == 0
    )
    assert calls[0]["base_url"] == "http://127.0.0.1:8000"
    assert calls[0]["repo_root"] == repo_root.resolve()
    assert calls[0]["user_folder"] == (tmp_path / "user").resolve()


def test_start_background_port_busy_exits_nonzero(tmp_path, monkeypatch):
    import tools.agent_seed.errors as agent_seed_errors

    def fake_start_node_background(**_kwargs):
        raise agent_seed_errors.AgentSeedPortInUseError("port busy")

    monkeypatch.setattr(
        agent_seed_node_lifecycle,
        "start_node_background",
        fake_start_node_background,
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    assert (
        agent_seed_cli.main(
            [
                "start-background",
                "--user-folder",
                str(tmp_path / "user"),
                "--repo-root",
                str(repo_root),
            ],
        )
        == 1
    )
