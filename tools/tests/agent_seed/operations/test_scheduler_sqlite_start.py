#  Scheduler DB env checks before start-background.

import pathlib

import pytest

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.scheduler_sqlite as agent_seed_scheduler_sqlite


def test_ensure_scheduler_sqlite_rejects_unset_scheduler_env(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    user_folder = repo_root / "user" / "agent-seed"
    user_folder.mkdir(parents=True)
    tasks_db = user_folder / "tasks.db"
    monkeypatch.setenv("NODE_SQLITE_FILE", str(tasks_db))
    monkeypatch.delenv("SCHEDULER_SQLITE_FILE", raising=False)

    with pytest.raises(agent_seed_errors.AgentSeedSchedulerSqliteConfigError) as error_info:
        agent_seed_scheduler_sqlite.ensure_scheduler_sqlite_for_agent_seed_start(
            user_folder,
            repo_root,
        )
    message = str(error_info.value)
    assert "SCHEDULER_SQLITE_FILE is not set" in message
    assert str((repo_root / "tasks.db").resolve()) in message
    assert str(tasks_db.resolve()) in message
    assert "automations" in message
    assert "seed-agent.sh --restart" in message


def test_ensure_scheduler_sqlite_rejects_same_path_outside_user_folder(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    user_folder = repo_root / "user" / "agent-seed"
    user_folder.mkdir(parents=True)
    outside_db = tmp_path / "other.db"
    monkeypatch.setenv("NODE_SQLITE_FILE", str(outside_db))
    monkeypatch.setenv("SCHEDULER_SQLITE_FILE", str(outside_db))

    with pytest.raises(agent_seed_errors.AgentSeedSchedulerSqliteConfigError) as error_info:
        agent_seed_scheduler_sqlite.ensure_scheduler_sqlite_for_agent_seed_start(
            user_folder,
            repo_root,
        )
    message = str(error_info.value)
    assert str((user_folder / "tasks.db").resolve()) in message
    assert str(outside_db.resolve()) in message


def test_ensure_scheduler_sqlite_rejects_mismatched_paths(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    user_folder = repo_root / "user" / "agent-seed"
    user_folder.mkdir(parents=True)
    expected_tasks = user_folder / "tasks.db"
    wrong_tasks = repo_root / "other-tasks.db"
    monkeypatch.setenv("NODE_SQLITE_FILE", str(expected_tasks))
    monkeypatch.setenv("SCHEDULER_SQLITE_FILE", str(wrong_tasks))

    with pytest.raises(agent_seed_errors.AgentSeedSchedulerSqliteConfigError) as error_info:
        agent_seed_scheduler_sqlite.ensure_scheduler_sqlite_for_agent_seed_start(
            user_folder,
            repo_root,
        )
    message = str(error_info.value)
    assert str(expected_tasks.resolve()) in message
    assert str(wrong_tasks.resolve()) in message


def test_ensure_scheduler_sqlite_accepts_aligned_paths(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    user_folder = repo_root / "user" / "agent-seed"
    user_folder.mkdir(parents=True)
    tasks_db = user_folder / "tasks.db"
    monkeypatch.setenv("NODE_SQLITE_FILE", str(tasks_db))
    monkeypatch.setenv("SCHEDULER_SQLITE_FILE", str(tasks_db))

    agent_seed_scheduler_sqlite.ensure_scheduler_sqlite_for_agent_seed_start(
        user_folder,
        repo_root,
    )


def test_ensure_scheduler_sqlite_accepts_repo_relative_env(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    user_folder = repo_root / "user" / "agent-seed"
    user_folder.mkdir(parents=True)
    rel = pathlib.Path("user/agent-seed/tasks.db")
    monkeypatch.setenv("NODE_SQLITE_FILE", rel.as_posix())
    monkeypatch.setenv("SCHEDULER_SQLITE_FILE", rel.as_posix())

    agent_seed_scheduler_sqlite.ensure_scheduler_sqlite_for_agent_seed_start(
        user_folder,
        repo_root,
    )
