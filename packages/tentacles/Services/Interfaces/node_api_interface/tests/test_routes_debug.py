#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import mock

import octobot_node.config
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

from datetime import datetime, timezone

from .conftest import ADMIN_ADDRESS, TENANT_ADDRESS


def _sample_debug_state() -> protocol_models.DebugState:
    return protocol_models.DebugState(
        version=sync_constants.DEBUG_STATE_VERSION,
        debug=protocol_models.Debug(automations=[], user_actions=[]),
    )


def _sample_debug_state_with_user_action() -> protocol_models.DebugState:
    user_action = protocol_models.UserAction(
        id="ua-serialize-test",
        configuration=protocol_models.UserActionConfiguration(
            protocol_models.StopAutomationConfiguration(
                action_type=protocol_models.UserActionType.AUTOMATION_STOP,
                id="00000000-0000-4000-8000-000000000099",
            )
        ),
        result=protocol_models.UserActionResult(
            protocol_models.AutomationActionResult(
                updated_at=datetime.now(timezone.utc),
                result_type=protocol_models.UserActionResultType.AUTOMATION,
            )
        ),
    )
    return protocol_models.DebugState(
        version=sync_constants.DEBUG_STATE_VERSION,
        debug=protocol_models.Debug(automations=[], user_actions=[user_action]),
    )


def _minimal_user_action_payload() -> dict:
    return {"id": "ua-api-test"}


def _signal_user_action_payload() -> dict:
    return {
        "id": "ua-signal-api-test",
        "configuration": {
            "action_type": "automation_signal",
            "automation_id": "00000000-0000-4000-8000-000000000099",
            "signal_type": "forced_trigger",
        },
    }


def _stop_automation_user_action_payload() -> dict:
    return {
        "id": "ua-stop-api-test",
        "configuration": {
            "action_type": "automation_stop",
            "id": "00000000-0000-4000-8000-000000000099",
        },
    }


def test_get_debug_returns_state_for_tenant_wallet(tenant_client, mock_auth):
    debug_state = _sample_debug_state()
    mock_get_debug_state = mock.AsyncMock(return_value=debug_state)
    with mock.patch(
        "octobot_node.protocol.debug.get_debug_state",
        new=mock_get_debug_state,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.get("/api/v1/debug/")
    assert response.status_code == 200
    assert response.json()["version"] == sync_constants.DEBUG_STATE_VERSION
    mock_get_debug_state.assert_awaited_once_with(TENANT_ADDRESS)


def test_get_debug_serializes_user_actions_without_oneof_validator_fields(
    tenant_client,
    mock_auth,
):
    debug_state = _sample_debug_state_with_user_action()
    mock_get_debug_state = mock.AsyncMock(return_value=debug_state)
    with mock.patch(
        "octobot_node.protocol.debug.get_debug_state",
        new=mock_get_debug_state,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.get("/api/v1/debug/")
    assert response.status_code == 200
    serialized_action = response.json()["debug"]["user_actions"][0]
    configuration = serialized_action["configuration"]
    result = serialized_action["result"]
    assert "oneof_schema_1_validator" not in configuration
    assert "actual_instance" not in configuration
    assert configuration["action_type"] == "automation_stop"
    assert "oneof_schema_1_validator" not in result
    assert "actual_instance" not in result
    assert result["result_type"] == "automation"


def test_get_debug_as_admin_with_wallet_address_query(tenant_client, mock_auth, admin_client):
    debug_state = _sample_debug_state()
    mock_get_debug_state = mock.AsyncMock(return_value=debug_state)
    with mock.patch(
        "octobot_node.protocol.debug.get_debug_state",
        new=mock_get_debug_state,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = admin_client.get(
                "/api/v1/debug/",
                params={"wallet_address": TENANT_ADDRESS},
            )
    assert response.status_code == 200
    mock_get_debug_state.assert_awaited_once_with(TENANT_ADDRESS)


def test_get_debug_as_tenant_with_wallet_address_query_forbidden(tenant_client, mock_auth):
    with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
        response = tenant_client.get(
            "/api/v1/debug/",
            params={"wallet_address": ADMIN_ADDRESS},
        )
    assert response.status_code == 403


def test_get_debug_tenant_with_own_wallet_address_query(tenant_client, mock_auth):
    debug_state = _sample_debug_state()
    mock_get_debug_state = mock.AsyncMock(return_value=debug_state)
    with mock.patch(
        "octobot_node.protocol.debug.get_debug_state",
        new=mock_get_debug_state,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.get(
                "/api/v1/debug/",
                params={"wallet_address": TENANT_ADDRESS},
            )
    assert response.status_code == 200
    mock_get_debug_state.assert_awaited_once_with(TENANT_ADDRESS)


def test_get_debug_requires_auth(client, mock_auth):
    response = client.get("/api/v1/debug/")
    assert response.status_code == 401


def test_get_debug_when_scheduler_not_initialized_returns_503(tenant_client, mock_auth):
    with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
        response = tenant_client.get("/api/v1/debug/")
    assert response.status_code == 503
    assert response.json()["detail"] == "Scheduler not initialized"


def test_post_user_action_executes_for_tenant_wallet(tenant_client, mock_auth):
    mock_execute_user_action = mock.AsyncMock(return_value=None)
    with mock.patch(
        "octobot_node.protocol.user_actions.execute_user_action",
        new=mock_execute_user_action,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
    assert response.status_code == 400
    assert response.json()["detail"] == "User action configuration is required"


def test_post_user_action_parses_flat_signal_configuration(tenant_client, mock_auth):
    mock_execute_user_action = mock.AsyncMock(return_value=None)
    with mock.patch(
        "octobot_node.protocol.user_actions.execute_user_action",
        new=mock_execute_user_action,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.post(
                "/api/v1/debug/",
                json=_signal_user_action_payload(),
            )
    assert response.status_code == 204
    assert response.content == b""
    user_action_argument = mock_execute_user_action.await_args[0][0]
    assert user_action_argument.id == "ua-signal-api-test"
    configuration = user_action_argument.configuration.actual_instance
    assert isinstance(configuration, protocol_models.SignalAutomationConfiguration)
    assert configuration.action_type == protocol_models.UserActionType.AUTOMATION_SIGNAL
    assert configuration.automation_id == "00000000-0000-4000-8000-000000000099"
    assert configuration.signal_type == protocol_models.AutomationSignalType.FORCED_TRIGGER
    assert mock_execute_user_action.await_args[0][1] == TENANT_ADDRESS


def test_post_user_action_parses_flat_stop_configuration(tenant_client, mock_auth):
    mock_execute_user_action = mock.AsyncMock(return_value=None)
    with mock.patch(
        "octobot_node.protocol.user_actions.execute_user_action",
        new=mock_execute_user_action,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.post(
                "/api/v1/debug/",
                json=_stop_automation_user_action_payload(),
            )
    assert response.status_code == 204
    user_action_argument = mock_execute_user_action.await_args[0][0]
    configuration = user_action_argument.configuration.actual_instance
    assert isinstance(configuration, protocol_models.StopAutomationConfiguration)
    assert configuration.id == "00000000-0000-4000-8000-000000000099"


def test_post_user_action_tenant_with_own_wallet_address_query(tenant_client, mock_auth):
    mock_execute_user_action = mock.AsyncMock(return_value=None)
    with mock.patch(
        "octobot_node.protocol.user_actions.execute_user_action",
        new=mock_execute_user_action,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.post(
                "/api/v1/debug/",
                json=_signal_user_action_payload(),
                params={"wallet_address": TENANT_ADDRESS},
            )
    assert response.status_code == 204
    assert mock_execute_user_action.await_args[0][1] == TENANT_ADDRESS


def test_post_user_action_tenant_with_other_wallet_forbidden(tenant_client, mock_auth):
    with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
        response = tenant_client.post(
            "/api/v1/debug/",
            json=_signal_user_action_payload(),
            params={"wallet_address": ADMIN_ADDRESS},
        )
    assert response.status_code == 403


def test_post_user_action_admin_with_wallet_address_query(admin_client, mock_auth):
    mock_execute_user_action = mock.AsyncMock(return_value=None)
    with mock.patch(
        "octobot_node.protocol.user_actions.execute_user_action",
        new=mock_execute_user_action,
    ):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = admin_client.post(
                "/api/v1/debug/",
                json=_signal_user_action_payload(),
                params={"wallet_address": TENANT_ADDRESS},
            )
    assert response.status_code == 204
    assert mock_execute_user_action.await_args[0][1] == TENANT_ADDRESS


def test_post_user_action_requires_auth(client, mock_auth):
    response = client.post("/api/v1/debug/", json=_minimal_user_action_payload())
    assert response.status_code == 401


def test_post_user_action_when_scheduler_not_initialized_returns_503(tenant_client, mock_auth):
    with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
        response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
    assert response.status_code == 503
    assert response.json()["detail"] == "Scheduler not initialized"


def test_get_debug_when_encryption_enabled_returns_404(tenant_client, mock_auth):
    mock_settings = mock.Mock(is_node_side_encryption_enabled=True)
    with mock.patch.object(octobot_node.config, "settings", mock_settings):
        response = tenant_client.get("/api/v1/debug/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Debug routes are disabled when node-side encryption is enabled"


def test_post_user_action_when_encryption_enabled_returns_404(tenant_client, mock_auth):
    mock_settings = mock.Mock(is_node_side_encryption_enabled=True)
    with mock.patch.object(octobot_node.config, "settings", mock_settings):
        response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
    assert response.status_code == 404
    assert response.json()["detail"] == "Debug routes are disabled when node-side encryption is enabled"
