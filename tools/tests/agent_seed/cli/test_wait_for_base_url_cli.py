#  Unit tests for agent seed wait-for-base-url CLI.

import tools.agent_seed.cli as agent_seed_cli
import tools.agent_seed.cli.wait_for_base_url as agent_seed_cli_wait_for_base_url
import tools.agent_seed.operations.wait_for_base_url as agent_seed_wait_for_base_url


def test_wait_for_base_url_subcommand_invokes_operation(monkeypatch):
    calls = []

    def fake_wait_for_base_url(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(agent_seed_wait_for_base_url, "wait_for_base_url", fake_wait_for_base_url)
    assert agent_seed_cli.main(["wait-for-base-url", "--base-url", "http://127.0.0.1:9000"]) == 0
    assert calls[0]["base_url"] == "http://127.0.0.1:9000"
    assert calls[0]["timeout_seconds"] == agent_seed_wait_for_base_url.DEFAULT_STARTUP_WAIT_SECONDS


def test_run_from_namespace_forwards_timeout_and_poll_interval(monkeypatch):
    calls = []

    def fake_wait_for_base_url(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(agent_seed_wait_for_base_url, "wait_for_base_url", fake_wait_for_base_url)
    namespace = agent_seed_cli.build_arg_parser().parse_args(
        [
            "wait-for-base-url",
            "--base-url",
            "http://node:8",
            "--timeout",
            "12",
            "--poll-interval",
            "0.5",
        ],
    )
    assert agent_seed_cli_wait_for_base_url.run_from_namespace(namespace) == 0
    assert calls[0] == {
        "base_url": "http://node:8",
        "timeout_seconds": 12.0,
        "poll_interval_seconds": 0.5,
    }
