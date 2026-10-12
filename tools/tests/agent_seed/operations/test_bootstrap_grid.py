#  Unit tests for agent seed grid bootstrap helpers.

import os

import pytest

import octobot_protocol.models as protocol_models

import octobot_node.agent_seed.constants as demo_agent_seed_constants

import tools.agent_seed.errors as agent_seed_errors
import tools.agent_seed.operations.bootstrap_grid as agent_seed_bootstrap_grid

GRID_ID = demo_agent_seed_constants.DEMO_AGENT_SEED_AUTOMATION_GRID_ID


class TestFindUserAction:
    def test_find_user_action_returns_matching_entry(self):
        debug_payload = {
            "debug": {
                "user_actions": [
                    {"id": "ua-other", "status": "completed"},
                    {"id": "ua-target", "status": "failed"},
                ],
            },
        }
        found = agent_seed_bootstrap_grid.find_user_action(debug_payload, "ua-target")
        assert found == {"id": "ua-target", "status": "failed"}

    def test_find_user_action_returns_none_when_missing(self):
        debug_payload = {"debug": {"user_actions": [{"id": "ua-other"}]}}
        assert agent_seed_bootstrap_grid.find_user_action(debug_payload, "ua-missing") is None


class TestFormatAutomationUserActionError:
    def test_format_includes_error_message_and_details(self):
        user_action = {
            "id": "ua-failed",
            "status": "failed",
            "result": {
                "actual_instance": {
                    "error_message": "invalid_automation_id",
                    "error_details": "AutomationConfiguration.id must be a valid UUID",
                },
            },
        }
        message = agent_seed_bootstrap_grid.format_automation_user_action_error(user_action)
        assert "ua-failed" in message
        assert "invalid_automation_id" in message
        assert "valid UUID" in message


class TestGridAutomationIsRunning:
    def test_matches_by_automation_id_not_only_display_name(self):
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": GRID_ID,
                        "status": protocol_models.WorkflowStatus.RUNNING.value,
                        "metadata": {"name": "other-name"},
                    },
                ],
            },
        }
        assert agent_seed_bootstrap_grid.grid_automation_is_running(debug_payload)


class TestEnsureGridAutomationCanBootstrap:
    def test_raises_when_grid_id_exists_completed(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_SQLITE_FILE", "/tmp/seed-tasks.db")
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": GRID_ID,
                        "status": protocol_models.WorkflowStatus.COMPLETED.value,
                    },
                ],
            },
        }
        with pytest.raises(agent_seed_errors.GridAutomationIdConflictError) as error_info:
            agent_seed_bootstrap_grid.ensure_grid_automation_can_bootstrap(debug_payload)
        message = str(error_info.value)
        assert GRID_ID in message
        assert "completed" in message
        assert os.path.abspath("/tmp/seed-tasks.db") in message
        assert "--clear" in message

    def test_no_op_when_running(self):
        debug_payload = {
            "debug": {
                "automations": [
                    {
                        "id": GRID_ID,
                        "status": protocol_models.WorkflowStatus.RUNNING.value,
                    },
                ],
            },
        }
        agent_seed_bootstrap_grid.ensure_grid_automation_can_bootstrap(debug_payload)


class TestEnsureUserActionNotFailed:
    def test_raises_runtime_error_when_action_failed(self):
        debug_payload = {
            "debug": {
                "user_actions": [
                    {
                        "id": "ua-failed",
                        "status": "failed",
                        "result": {
                            "actual_instance": {
                                "error_message": "invalid_automation_id",
                                "error_details": "bad id",
                            },
                        },
                    },
                ],
            },
        }
        with pytest.raises(RuntimeError, match="invalid_automation_id"):
            agent_seed_bootstrap_grid.ensure_user_action_not_failed(debug_payload, "ua-failed")

    def test_no_op_when_action_pending_or_missing(self):
        debug_payload = {
            "debug": {
                "user_actions": [
                    {"id": "ua-pending", "status": "pending"},
                ],
            },
        }
        agent_seed_bootstrap_grid.ensure_user_action_not_failed(debug_payload, "ua-pending")
        agent_seed_bootstrap_grid.ensure_user_action_not_failed(debug_payload, "ua-missing")

    def test_no_op_when_action_completed(self):
        debug_payload = {
            "debug": {
                "user_actions": [{"id": "ua-done", "status": "completed"}],
            },
        }
        agent_seed_bootstrap_grid.ensure_user_action_not_failed(debug_payload, "ua-done")
