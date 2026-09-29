#  Unit tests for agent seed bootstrap CLI scenario options.

import pytest

import tools.agent_seed.cli as agent_seed_cli
import tools.agent_seed.cli.bootstrap as agent_seed_cli_bootstrap
import tools.agent_seed.enums as agent_seed_enums
import tools.agent_seed.operations.bootstrap_scenarios as agent_seed_bootstrap_scenarios


@pytest.fixture
def captured_run(monkeypatch):
    calls = []

    def fake_run_scenarios(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(agent_seed_bootstrap_scenarios, "run_scenarios", fake_run_scenarios)
    return calls


class TestBootstrapCli:
    def test_no_scenario_option_passes_empty_list(self, captured_run):
        assert agent_seed_cli.main(["bootstrap"]) == 0
        assert captured_run[0]["scenarios"] == []

    def test_scenario_option_is_repeatable(self, captured_run):
        argv = ["bootstrap", "--scenario", "index", "--scenario", "lifecycle"]
        assert agent_seed_cli.main(argv) == 0
        assert captured_run[0]["scenarios"] == [
            agent_seed_enums.BootstrapScenario.INDEX,
            agent_seed_enums.BootstrapScenario.LIFECYCLE,
        ]

    def test_unknown_scenario_is_rejected(self, captured_run):
        with pytest.raises(SystemExit):
            agent_seed_cli.main(["bootstrap", "--scenario", "errored"])
        assert captured_run == []

    def test_run_from_namespace_forwards_scenarios_and_base_url(self, captured_run):
        namespace = agent_seed_cli.build_arg_parser().parse_args(
            ["bootstrap", "--base-url", "http://node:9", "--scenario", "all"],
        )
        assert agent_seed_cli_bootstrap.run_from_namespace(namespace) == 0
        assert captured_run[0]["base_url"] == "http://node:9"
        assert captured_run[0]["scenarios"] == [agent_seed_enums.BootstrapScenario.ALL]

    def test_all_subcommand_accepts_scenarios(self):
        namespace = agent_seed_cli.build_arg_parser().parse_args(["all", "--scenario", "completed"])
        assert namespace.scenario == ["completed"]
