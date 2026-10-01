#  Unit tests for agent seed grid bootstrap helpers.

import pytest

import tools.agent_seed.operations.bootstrap_grid as agent_seed_bootstrap_grid


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
        found = agent_seed_bootstrap_grid._find_user_action(debug_payload, "ua-target")
        assert found == {"id": "ua-target", "status": "failed"}

    def test_find_user_action_returns_none_when_missing(self):
        debug_payload = {"debug": {"user_actions": [{"id": "ua-other"}]}}
        assert agent_seed_bootstrap_grid._find_user_action(debug_payload, "ua-missing") is None


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
        message = agent_seed_bootstrap_grid._format_automation_user_action_error(user_action)
        assert "ua-failed" in message
        assert "invalid_automation_id" in message
        assert "valid UUID" in message


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
            agent_seed_bootstrap_grid._ensure_user_action_not_failed(debug_payload, "ua-failed")

    def test_no_op_when_action_pending_or_missing(self):
        debug_payload = {
            "debug": {
                "user_actions": [
                    {"id": "ua-pending", "status": "pending"},
                ],
            },
        }
        agent_seed_bootstrap_grid._ensure_user_action_not_failed(debug_payload, "ua-pending")
        agent_seed_bootstrap_grid._ensure_user_action_not_failed(debug_payload, "ua-missing")

    def test_no_op_when_action_completed(self):
        debug_payload = {
            "debug": {
                "user_actions": [{"id": "ua-done", "status": "completed"}],
            },
        }
        agent_seed_bootstrap_grid._ensure_user_action_not_failed(debug_payload, "ua-done")
