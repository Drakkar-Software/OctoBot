#  Unit tests for shared bootstrap automation helpers.

import os

import pytest

import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.bootstrap_automation as agent_seed_bootstrap_automation

class TestFindAutomation:
    def test_returns_matching_automation(self):
        payload = {"debug": {"automations": [{"id": "a"}, {"id": "b", "status": "running"}]}}
        assert agent_seed_bootstrap_automation.find_automation(payload, "b") == {
            "id": "b",
            "status": "running",
        }

    def test_returns_none_when_missing_or_empty(self):
        assert agent_seed_bootstrap_automation.find_automation({"debug": {"automations": []}}, "a") is None
        assert agent_seed_bootstrap_automation.find_automation({}, "a") is None


class TestAutomationIsRunning:
    def test_matches_by_automation_id(self):
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                        "status": protocol_models.WorkflowStatus.RUNNING.value,
                        "metadata": {"name": "other-name"},
                    },
                ],
            },
        }
        assert agent_seed_bootstrap_automation.automation_is_running(debug_payload, demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID)


class TestEnsureAutomationIdAvailableForCreate:
    def test_raises_when_id_exists_completed(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_SQLITE_FILE", "/tmp/seed-tasks.db")
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_INDEX_ID,
                        "status": protocol_models.WorkflowStatus.COMPLETED.value,
                    },
                ],
            },
        }
        with pytest.raises(agent_seed_errors.AutomationIdConflictError) as error_info:
            agent_seed_bootstrap_automation.ensure_automation_id_available_for_create(
                debug_payload,
                demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_INDEX_ID,
            )
        message = str(error_info.value)
        assert demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_INDEX_ID in message
        assert "completed" in message
        assert os.path.abspath("/tmp/seed-tasks.db") in message
        assert "--clear" in message

    def test_raises_on_pending_before_create(self, monkeypatch):
        monkeypatch.setenv("NODE_SQLITE_FILE", "/tmp/seed-tasks.db")
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                        "status": protocol_models.WorkflowStatus.PENDING.value,
                    },
                ],
            },
        }
        with pytest.raises(agent_seed_errors.AutomationIdConflictError):
            agent_seed_bootstrap_automation.ensure_automation_id_available_for_create(
                debug_payload,
                demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
            )

    def test_no_op_when_running(self):
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                        "status": protocol_models.WorkflowStatus.RUNNING.value,
                    },
                ],
            },
        }
        agent_seed_bootstrap_automation.ensure_automation_id_available_for_create(debug_payload, demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID)


class TestEnsureAutomationNotStaleWhileWaitingRunning:
    def test_allows_pending_while_waiting(self):
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                        "status": protocol_models.WorkflowStatus.PENDING.value,
                    },
                ],
            },
        }
        agent_seed_bootstrap_automation.ensure_automation_not_stale_while_waiting_running(
            debug_payload,
            demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
        )

    def test_raises_on_completed_while_waiting(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_SQLITE_FILE", "/tmp/seed-tasks.db")
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
                        "status": protocol_models.WorkflowStatus.COMPLETED.value,
                    },
                ],
            },
        }
        with pytest.raises(agent_seed_errors.AutomationIdConflictError):
            agent_seed_bootstrap_automation.ensure_automation_not_stale_while_waiting_running(
                debug_payload,
                demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID,
            )
