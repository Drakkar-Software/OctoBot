#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Node bridge/transform layer for protocol wire compatibility: wire fixtures and flow
# entities fed through node protocol bridges (privacy_filter, automations_protocol)
# must produce wire-safe protocol output (credentials stripped, automation state shape
# matches fixture).

import json

import dbos
import octobot_flow.entities as flow_entities
import octobot_node.models as node_models
import octobot_protocol.models as protocol_models
import scripts.lib.openapi_compat_lib as openapi_compat_lib

import octobot_node.protocol.automations as automations_protocol
import octobot_node.protocol.util.privacy_filter as privacy_filter


def _minimal_automation_task_content() -> str:
    state_dict = {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {
                "actions": [
                    {"id": "a1", "action": "apply_configuration", "config": {}},
                ],
            },
            "execution": {
                "previous_execution": {"triggered_at": 0},
                "current_execution": {"triggered_at": 0},
            },
        },
    }
    return json.dumps({"state": state_dict})


def _assert_account_authentication_credentials_stripped(
    authentication: protocol_models.AccountAuthentication,
) -> None:
    assert authentication.api_key is None
    assert authentication.api_secret is None
    assert authentication.api_passphrase is None
    assert authentication.public_key is None
    assert authentication.private_key is None
    assert authentication.seed_phrase is None


class TestProtocolWireCompatBridge:
    def test_account_auth_wire_fixtures_strip_credentials(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        user_actions_dir = version_dir / "user_actions"
        auth_fixture_names = ("account_auth_create.json", "account_auth_edit.json")
        for fixture_name in auth_fixture_names:
            fixture_path = user_actions_dir / fixture_name
            with open(fixture_path, encoding="utf-8") as handle:
                fixture_payload = json.load(handle)
            wire_user_action = protocol_models.UserAction.from_json(json.dumps(fixture_payload))
            protocol_user_action = privacy_filter.to_protocol_user_action(wire_user_action)
            assert protocol_user_action.id == wire_user_action.id
            authentication = (
                protocol_user_action.configuration.actual_instance.configuration
            )
            assert authentication.id is not None
            _assert_account_authentication_credentials_stripped(authentication)

    def test_automation_state_wire_fixture_matches_bridge_shape(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        with open(version_dir / "automation_state.json", encoding="utf-8") as handle:
            wire_fixture = json.load(handle)
        task = node_models.Task(
            id=str(wire_fixture["id"]),
            name=str(wire_fixture["metadata"]["name"]),
            content=_minimal_automation_task_content(),
            type="execute_actions",
        )
        bridged_state = automations_protocol._to_protocol_automation_state(
            task,
            workflow_status=dbos.WorkflowStatusString.PENDING.value,
        )
        reparsed_state = protocol_models.AutomationState.from_json(bridged_state.to_json())
        assert reparsed_state.id == wire_fixture["id"]
        assert reparsed_state.metadata.name == wire_fixture["metadata"]["name"]
        assert reparsed_state.status.value == wire_fixture["status"]

    def test_automation_apply_configuration_redacts_credentials_in_bridge(self):
        configured_action = flow_entities.ConfiguredActionDetails(
            id="c1",
            action="apply_configuration",
            config={
                "exchange_account_details": {
                    "auth_details": {
                        "api_key": "secret-key",
                        "api_secret": "secret-secret",
                        "api_password": "secret-pass",
                    },
                },
            },
        )
        flow_state = flow_entities.AutomationState(
            automation=flow_entities.AutomationDetails(
                metadata=flow_entities.AutomationMetadata(automation_id="automation_1"),
                actions_dag=flow_entities.ActionsDAG(actions=[configured_action]),
            ),
        )
        base_state = protocol_models.AutomationState(
            id="task-1",
            status=protocol_models.WorkflowStatus.PENDING,
            metadata=protocol_models.AutomationMetadata(
                name="task-name",
                description="",
            ),
        )
        filled_state = automations_protocol._fill_protocol_automation_state(
            base_state,
            flow_state,
        )
        assert filled_state.actions is not None
        auth_details = filled_state.actions[0].configuration["exchange_account_details"]["auth_details"]
        assert "api_key" not in auth_details
        assert "api_secret" not in auth_details
        assert "api_password" not in auth_details
