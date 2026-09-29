#  Unit tests for agent seed bootstrap scenarios (index, completed, lifecycle).

import pytest

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.enums as agent_seed_enums
import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.bootstrap_http as agent_seed_bootstrap_http
import tools.agent_seed.operations.bootstrap_scenarios as agent_seed_bootstrap_scenarios

BASE_URL = "http://127.0.0.1:8000"
GRID_ID = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID
INDEX_ID = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_INDEX_ID
COMPLETED_ID = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_COMPLETED_ID
GRID_NAME = demo_agent_seed_constants.DEMO_AGENT_SEED_GRID_AUTOMATION_DISPLAY_NAME


class FakeNode:
    """In-memory stand-in for GET/POST /api/v1/debug/ that completes every user action at once."""

    def __init__(self, *, drop_name_on_restart: bool = False, reject_posts_with: int | None = None):
        self.automations: dict[str, dict] = {}
        self.user_actions: list[dict] = []
        self.posted_action_types: list[str] = []
        self.drop_name_on_restart = drop_name_on_restart
        self.reject_posts_with = reject_posts_with

    def request_json(self, method, url, headers, payload=None):
        assert url.endswith("/api/v1/debug/")
        assert headers["Authorization"].startswith("Basic ")
        if method == "GET":
            return 200, {
                "debug": {
                    "automations": list(self.automations.values()),
                    "user_actions": self.user_actions,
                },
            }
        if self.reject_posts_with is not None:
            return self.reject_posts_with, {"detail": "rejected"}
        self._apply(payload)
        return 204, None

    def _apply(self, payload):
        action = payload["configuration"]
        action_type = action["action_type"]
        self.posted_action_types.append(action_type)
        if action_type == "automation_create":
            configuration = action["configuration"]
            self.automations[configuration["id"]] = {
                "id": configuration["id"],
                "status": "running",
                "metadata": {"name": configuration["name"]},
            }
        elif action_type == "automation_stop":
            self.automations[action["id"]]["status"] = "completed"
        elif action_type == "automation_restart":
            automation = self.automations[action["id"]]
            automation["status"] = "running"
            if self.drop_name_on_restart:
                automation["metadata"]["name"] = ""
        self.user_actions.append({"id": payload["id"], "status": "completed"})


@pytest.fixture
def fake_node(monkeypatch):
    node = FakeNode()
    monkeypatch.setattr(agent_seed_bootstrap_http, "request_json", node.request_json)
    return node


def _run(scenarios):
    agent_seed_bootstrap_scenarios.run_scenarios(
        base_url=BASE_URL,
        scenarios=scenarios,
        poll_interval_seconds=0,
        timeout_seconds=1,
    )


class TestExpandScenarios:
    def test_defaults_to_grid(self):
        assert agent_seed_bootstrap_scenarios.expand_scenarios(None) == [agent_seed_enums.BootstrapScenario.GRID]
        assert agent_seed_bootstrap_scenarios.expand_scenarios([]) == [agent_seed_enums.BootstrapScenario.GRID]

    def test_all_expands_in_dependency_order(self):
        assert agent_seed_bootstrap_scenarios.expand_scenarios([agent_seed_enums.BootstrapScenario.ALL]) == [
            agent_seed_enums.BootstrapScenario.GRID,
            agent_seed_enums.BootstrapScenario.INDEX,
            agent_seed_enums.BootstrapScenario.COMPLETED,
            agent_seed_enums.BootstrapScenario.LIFECYCLE,
        ]

    def test_order_is_fixed_and_duplicates_dropped(self):
        requested = [
            agent_seed_enums.BootstrapScenario.LIFECYCLE,
            agent_seed_enums.BootstrapScenario.INDEX,
            agent_seed_enums.BootstrapScenario.INDEX,
        ]
        assert agent_seed_bootstrap_scenarios.expand_scenarios(requested) == [
            agent_seed_enums.BootstrapScenario.INDEX,
            agent_seed_enums.BootstrapScenario.LIFECYCLE,
        ]


class TestFindAutomation:
    def test_returns_matching_automation(self):
        payload = {"debug": {"automations": [{"id": "a"}, {"id": "b", "status": "running"}]}}
        assert agent_seed_bootstrap_scenarios.find_automation(payload, "b") == {"id": "b", "status": "running"}

    def test_returns_none_when_missing_or_empty(self):
        assert agent_seed_bootstrap_scenarios.find_automation({"debug": {"automations": []}}, "a") is None
        assert agent_seed_bootstrap_scenarios.find_automation({}, "a") is None


class TestIndexScenario:
    def test_creates_running_index_automation(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.INDEX])
        assert fake_node.posted_action_types == ["automation_create"]
        assert fake_node.automations[INDEX_ID]["status"] == "running"
        assert (
            fake_node.automations[INDEX_ID]["metadata"]["name"]
            == demo_agent_seed_constants.DEMO_AGENT_SEED_INDEX_AUTOMATION_DISPLAY_NAME
        )

    def test_no_op_when_already_running(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.INDEX])
        _run([agent_seed_enums.BootstrapScenario.INDEX])
        assert fake_node.posted_action_types == ["automation_create"]

    def test_raises_when_node_rejects_the_action(self, monkeypatch):
        node = FakeNode(reject_posts_with=403)
        monkeypatch.setattr(agent_seed_bootstrap_http, "request_json", node.request_json)
        with pytest.raises(RuntimeError, match="HTTP 403"):
            _run([agent_seed_enums.BootstrapScenario.INDEX])


class TestCompletedScenario:
    def test_creates_then_stops_automation(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.COMPLETED])
        assert fake_node.posted_action_types == ["automation_create", "automation_stop"]
        assert fake_node.automations[COMPLETED_ID]["status"] == "completed"

    def test_no_op_when_already_completed(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.COMPLETED])
        _run([agent_seed_enums.BootstrapScenario.COMPLETED])
        assert fake_node.posted_action_types == ["automation_create", "automation_stop"]

    def test_only_stops_when_already_running(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.COMPLETED])
        fake_node.automations[COMPLETED_ID]["status"] = "running"
        _run([agent_seed_enums.BootstrapScenario.COMPLETED])
        assert fake_node.posted_action_types == ["automation_create", "automation_stop", "automation_stop"]

    def test_times_out_when_automation_never_completes(self, fake_node, monkeypatch):
        original_apply = fake_node._apply

        def apply_without_stopping(payload):
            if payload["configuration"]["action_type"] != "automation_stop":
                original_apply(payload)

        monkeypatch.setattr(fake_node, "_apply", apply_without_stopping)
        with pytest.raises(TimeoutError, match="completed"):
            _run([agent_seed_enums.BootstrapScenario.COMPLETED])


class TestLifecycleScenario:
    def test_passes_when_name_survives_restart(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.LIFECYCLE])
        assert fake_node.posted_action_types == ["automation_create", "automation_stop", "automation_restart"]
        assert fake_node.automations[GRID_ID]["status"] == "running"
        assert fake_node.automations[GRID_ID]["metadata"]["name"] == GRID_NAME

    def test_raises_typed_error_when_name_lost_on_restart(self, monkeypatch):
        node = FakeNode(drop_name_on_restart=True)
        monkeypatch.setattr(agent_seed_bootstrap_http, "request_json", node.request_json)
        with pytest.raises(agent_seed_errors.AutomationNameLostError, match="name is ''"):
            _run([agent_seed_enums.BootstrapScenario.LIFECYCLE])

    def test_name_lost_error_is_an_agent_seed_error(self):
        assert issubclass(agent_seed_errors.AutomationNameLostError, agent_seed_errors.AgentSeedError)


class TestAllScenarios:
    def test_all_runs_every_scenario_in_order(self, fake_node):
        _run([agent_seed_enums.BootstrapScenario.ALL])
        assert fake_node.posted_action_types == [
            "automation_create",  # grid
            "automation_create",  # index
            "automation_create",  # completed
            "automation_stop",
            "automation_stop",  # lifecycle
            "automation_restart",
        ]
