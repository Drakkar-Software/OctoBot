#  Unit tests for agent-seed node pidfile, port checks, and stop.

import pytest

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.node_lifecycle as agent_seed_node_lifecycle
import tools.agent_seed.paths as agent_seed_paths


def test_prepare_node_start_raises_when_recorded_pid_still_running(tmp_path, monkeypatch):
    pid_file = agent_seed_paths.node_pid_file(tmp_path)
    pid_file.write_text("4242\n", encoding="utf-8")
    monkeypatch.setattr(agent_seed_node_lifecycle, "is_process_running", lambda pid: pid == 4242)

    with pytest.raises(agent_seed_errors.AgentSeedPortInUseError, match="recorded node is still running"):
        agent_seed_node_lifecycle.prepare_node_start(tmp_path, "http://127.0.0.1:8000")


def test_prepare_node_start_removes_stale_pidfile_and_checks_port(tmp_path, monkeypatch):
    pid_file = agent_seed_paths.node_pid_file(tmp_path)
    pid_file.write_text("4242\n", encoding="utf-8")
    monkeypatch.setattr(agent_seed_node_lifecycle, "is_process_running", lambda _pid: False)
    monkeypatch.setattr(agent_seed_node_lifecycle, "ensure_port_free_for_start", lambda _url: None)

    agent_seed_node_lifecycle.prepare_node_start(tmp_path, "http://127.0.0.1:8000")
    assert not pid_file.is_file()


def test_ensure_port_free_for_start_raises_when_port_accepts_connections(monkeypatch):
    monkeypatch.setattr(
        agent_seed_node_lifecycle.agent_seed_base_url_net,
        "is_tcp_port_accepting",
        lambda host, port: host == "127.0.0.1" and port == 8000,
    )
    monkeypatch.setattr(agent_seed_node_lifecycle, "find_listener_pids", lambda port: [99])

    with pytest.raises(agent_seed_errors.AgentSeedPortInUseError, match="port 8000 is already in use"):
        agent_seed_node_lifecycle.ensure_port_free_for_start("http://127.0.0.1:8000")


def test_stop_recorded_node_no_pidfile_port_free(tmp_path, monkeypatch):
    monkeypatch.setattr(
        agent_seed_node_lifecycle.agent_seed_base_url_net,
        "is_tcp_port_accepting",
        lambda host, port: False,
    )
    message = agent_seed_node_lifecycle.stop_recorded_node(tmp_path, "http://127.0.0.1:8000")
    assert "No agent-seed node recorded" in message


def test_stop_recorded_node_no_pidfile_port_busy_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        agent_seed_node_lifecycle.agent_seed_base_url_net,
        "is_tcp_port_accepting",
        lambda host, port: True,
    )
    monkeypatch.setattr(agent_seed_node_lifecycle, "find_listener_pids", lambda port: [12])

    with pytest.raises(agent_seed_errors.AgentSeedNodeStopError, match="No agent-seed pidfile"):
        agent_seed_node_lifecycle.stop_recorded_node(tmp_path, "http://127.0.0.1:8000")


def test_stop_recorded_node_terminates_and_removes_pidfile(tmp_path, monkeypatch):
    pid_file = agent_seed_paths.node_pid_file(tmp_path)
    pid_file.write_text("5001\n", encoding="utf-8")
    terminated: list[int] = []

    def fake_terminate(pid, _timeout):
        terminated.append(pid)

    monkeypatch.setattr(agent_seed_node_lifecycle, "_terminate_pid", fake_terminate)
    monkeypatch.setattr(
        agent_seed_node_lifecycle.agent_seed_base_url_net,
        "is_tcp_port_accepting",
        lambda host, port: False,
    )

    message = agent_seed_node_lifecycle.stop_recorded_node(tmp_path, "http://127.0.0.1:8000")
    assert terminated == [5001]
    assert not pid_file.is_file()
    assert "Stopped agent-seed node" in message


def test_resolve_stop_timeout_seconds_uses_env(monkeypatch):
    monkeypatch.setenv("AGENT_SEED_STOP_WAIT_SEC", "42")
    assert agent_seed_node_lifecycle.resolve_stop_timeout_seconds(None) == 42.0
    assert agent_seed_node_lifecycle.resolve_stop_timeout_seconds(7.0) == 7.0


def test_start_node_background_writes_pidfile_and_prepares(tmp_path, monkeypatch):
    user_folder = tmp_path / "user"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "start.py").write_text("# stub\n", encoding="utf-8")
    prepare_calls = []
    monkeypatch.setattr(
        agent_seed_node_lifecycle,
        "prepare_node_start",
        lambda folder, url: prepare_calls.append((folder, url)),
    )

    class FakeProcess:
        pid = 12345

    def fake_popen(*_args, **_kwargs):
        return FakeProcess()

    monkeypatch.setattr(agent_seed_node_lifecycle.subprocess, "Popen", fake_popen)

    message = agent_seed_node_lifecycle.start_node_background(
        user_folder=user_folder,
        base_url="http://127.0.0.1:8000",
        repo_root=repo_root,
    )
    assert prepare_calls == [(user_folder, "http://127.0.0.1:8000")]
    pid_file = agent_seed_paths.node_pid_file(user_folder)
    assert pid_file.read_text(encoding="utf-8").strip() == "12345"
    assert "12345" in message
    assert str(agent_seed_paths.node_log_file(user_folder)) in message


def test_stop_recorded_node_raises_when_port_still_busy_after_stop(tmp_path, monkeypatch):
    pid_file = agent_seed_paths.node_pid_file(tmp_path)
    pid_file.write_text("5002\n", encoding="utf-8")
    monkeypatch.setattr(agent_seed_node_lifecycle, "_terminate_pid", lambda _pid, _timeout: None)
    monkeypatch.setattr(
        agent_seed_node_lifecycle.agent_seed_base_url_net,
        "is_tcp_port_accepting",
        lambda host, port: True,
    )
    monkeypatch.setattr(agent_seed_node_lifecycle, "find_listener_pids", lambda port: [77])

    with pytest.raises(agent_seed_errors.AgentSeedNodeStopError, match="already in use"):
        agent_seed_node_lifecycle.stop_recorded_node(tmp_path, "http://127.0.0.1:8000")
    assert not pid_file.is_file()
