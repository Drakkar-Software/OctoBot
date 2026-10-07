#  Unit tests for agent-seed node startup wait helper.

import socket

import pytest

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.wait_for_base_url as agent_seed_wait_for_base_url


def test_wait_for_base_url_returns_when_connect_succeeds(monkeypatch):
    def fake_create_connection(address, timeout=0):
        assert address == ("127.0.0.1", 8000)
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    monkeypatch.setattr(agent_seed_wait_for_base_url.socket, "create_connection", fake_create_connection)
    agent_seed_wait_for_base_url.wait_for_base_url(
        "http://127.0.0.1:8000",
        timeout_seconds=1.0,
        poll_interval_seconds=0.01,
    )


def test_wait_for_base_url_raises_after_timeout(monkeypatch):
    def fake_create_connection(address, timeout=0):
        raise OSError("connection refused")

    monkeypatch.setattr(agent_seed_wait_for_base_url.socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(agent_seed_wait_for_base_url.time, "sleep", lambda _seconds: None)
    with pytest.raises(agent_seed_errors.AgentSeedNodeStartupTimeoutError, match="Timed out after 1s"):
        agent_seed_wait_for_base_url.wait_for_base_url(
            "http://127.0.0.1:8000",
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
        )
