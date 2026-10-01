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

import base64
import contextlib
import json
import mock
import pytest

import octobot_node.agent_seed.constants as demo_agent_seed_constants
import octobot_node.agent_seed.demo_wallet as demo_agent_seed_wallet
import octobot_node.config
import octobot_node.scheduler
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

from datetime import datetime, timezone

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE, ADMIN_USER_ID, TENANT_ADDRESS, TENANT_USER_ID

_DEBUG_ROUTE_MODULE = "tentacles.Services.Interfaces.node_api_interface.api.routes.debug"


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


def _restart_automation_user_action_payload() -> dict:
    return {
        "id": "ua-restart-api-test",
        "configuration": {
            "action_type": "automation_restart",
            "id": "00000000-0000-4000-8000-000000000099",
        },
    }


_AUTOMATION_PARENT_ID = "00000000-0000-4000-8000-000000000099"


@contextlib.contextmanager
def _automation_owned_by_caller():
    with mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_active_automation_workflow_ids_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=[f"{_AUTOMATION_PARENT_ID}_1"],
    ):
        yield


@contextlib.contextmanager
def _automation_not_owned_by_caller(*, owner_user_id: str):
    with mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_active_automation_workflow_ids_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=[],
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_latest_terminal_automation_workflow_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_automation_owner_user_id",
        new_callable=mock.AsyncMock,
        return_value=owner_user_id,
    ):
        yield


@contextlib.contextmanager
def _automation_not_found():
    with mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_active_automation_workflow_ids_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=[],
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_automation_owner_user_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_latest_terminal_automation_workflow_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_terminal_automation_owner_user_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ):
        yield


@contextlib.contextmanager
def _terminal_automation_owned_by_caller():
    with mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_active_automation_workflow_ids_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=[],
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_latest_terminal_automation_workflow_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=mock.Mock(),
    ):
        yield


@contextlib.contextmanager
def _terminal_automation_not_owned_by_caller(*, owner_user_id: str):
    with mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_active_automation_workflow_ids_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=[],
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_latest_terminal_automation_workflow_for_parent_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_automation_owner_user_id",
        new_callable=mock.AsyncMock,
        return_value=None,
    ), mock.patch.object(
        octobot_node.scheduler.SCHEDULER,
        "resolve_terminal_automation_owner_user_id",
        new_callable=mock.AsyncMock,
        return_value=owner_user_id,
    ):
        yield


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _assert_auth_error_response(response, expected_code: str) -> None:
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == expected_code


class TestGetDebug:
    def test_returns_state_for_tenant_wallet(self, tenant_client, mock_auth):
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
        mock_get_debug_state.assert_awaited_once_with(TENANT_USER_ID)

    def test_serializes_user_actions_without_oneof_validator_fields(
        self,
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

    def test_as_admin_with_wallet_address_query(self, admin_client, mock_auth):
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
        mock_get_debug_state.assert_awaited_once_with(TENANT_USER_ID)

    def test_as_tenant_with_other_wallet_address_query_forbidden(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.get(
                "/api/v1/debug/",
                params={"wallet_address": ADMIN_ADDRESS},
            )
        assert response.status_code == 403

    def test_tenant_with_own_wallet_address_query(self, tenant_client, mock_auth):
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
        mock_get_debug_state.assert_awaited_once_with(TENANT_USER_ID)

    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.get("/api/v1/debug/")
        assert response.status_code == 401

    def test_wrong_passphrase_returns_401(self, client, mock_auth):
        response = client.get(
            "/api/v1/debug/",
            headers=_auth_header(TENANT_ADDRESS, "wrong"),
        )
        _assert_auth_error_response(response, "auth_invalid_passphrase")

    def test_unknown_wallet_returns_401(self, client, mock_auth):
        response = client.get(
            "/api/v1/debug/",
            headers=_auth_header("0xdeadbeef", ADMIN_PASSPHRASE),
        )
        _assert_auth_error_response(response, "auth_wallet_not_found")

    def test_when_scheduler_not_initialized_returns_503(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            response = tenant_client.get("/api/v1/debug/")
        assert response.status_code == 503
        assert response.json()["detail"] == "Scheduler not initialized"

    def test_when_encryption_enabled_returns_404(self, tenant_client, mock_auth):
        mock_settings = mock.Mock(is_node_side_encryption_enabled=True)
        with mock.patch.object(octobot_node.config, "settings", mock_settings):
            response = tenant_client.get("/api/v1/debug/")
        assert response.status_code == 404
        assert response.json()["detail"] == "Debug routes are disabled when node-side encryption is enabled"


class TestExecuteUserAction:
    def test_missing_configuration_returns_400(self, tenant_client, mock_auth):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
        assert response.status_code == 400
        assert response.json()["detail"] == "User action configuration is required"

    def test_parses_flat_signal_configuration(self, tenant_client, mock_auth):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_owned_by_caller():
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
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    def test_parses_flat_stop_configuration(self, tenant_client, mock_auth):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_owned_by_caller():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=_stop_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        user_action_argument = mock_execute_user_action.await_args[0][0]
        configuration = user_action_argument.configuration.actual_instance
        assert isinstance(configuration, protocol_models.StopAutomationConfiguration)
        assert configuration.id == "00000000-0000-4000-8000-000000000099"

    def test_tenant_with_own_wallet_address_query(self, tenant_client, mock_auth):
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
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    def test_tenant_with_other_wallet_forbidden(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
            response = tenant_client.post(
                "/api/v1/debug/",
                json=_signal_user_action_payload(),
                params={"wallet_address": ADMIN_ADDRESS},
            )
        assert response.status_code == 403

    def test_admin_with_wallet_address_query(self, admin_client, mock_auth):
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
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.post("/api/v1/debug/", json=_minimal_user_action_payload())
        assert response.status_code == 401

    def test_wrong_passphrase_returns_401(self, client, mock_auth):
        response = client.post(
            "/api/v1/debug/",
            json=_minimal_user_action_payload(),
            headers=_auth_header(TENANT_ADDRESS, "wrong"),
        )
        _assert_auth_error_response(response, "auth_invalid_passphrase")

    def test_unknown_wallet_returns_401(self, client, mock_auth):
        response = client.post(
            "/api/v1/debug/",
            json=_minimal_user_action_payload(),
            headers=_auth_header("0xdeadbeef", ADMIN_PASSPHRASE),
        )
        _assert_auth_error_response(response, "auth_wallet_not_found")

    def test_when_scheduler_not_initialized_returns_503(self, tenant_client, mock_auth):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
        assert response.status_code == 503
        assert response.json()["detail"] == "Scheduler not initialized"

    def test_when_encryption_enabled_returns_404(self, tenant_client, mock_auth):
        mock_settings = mock.Mock(is_node_side_encryption_enabled=True)
        with mock.patch.object(octobot_node.config, "settings", mock_settings):
            response = tenant_client.post("/api/v1/debug/", json=_minimal_user_action_payload())
        assert response.status_code == 404
        assert response.json()["detail"] == "Debug routes are disabled when node-side encryption is enabled"


class TestExecuteUserActionCrossWalletAutomation:
    @pytest.mark.parametrize(
        "payload_factory",
        [
            _stop_automation_user_action_payload,
            _signal_user_action_payload,
            _restart_automation_user_action_payload,
        ],
    )
    def test_admin_without_wallet_address_uses_owner_user_id(
        self,
        admin_client,
        mock_auth,
        payload_factory,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_not_owned_by_caller(owner_user_id=TENANT_USER_ID):
                    response = admin_client.post(
                        "/api/v1/debug/",
                        json=payload_factory(),
                    )
        assert response.status_code == 204
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    @pytest.mark.parametrize(
        "payload_factory",
        [
            _stop_automation_user_action_payload,
            _signal_user_action_payload,
            _restart_automation_user_action_payload,
        ],
    )
    def test_non_admin_without_wallet_address_returns_404_when_not_owned(
        self,
        tenant_client,
        mock_auth,
        payload_factory,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_not_found():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=payload_factory(),
                    )
        assert response.status_code == 404
        assert response.json()["detail"] == "Automation not found"
        mock_execute_user_action.assert_not_awaited()

    def test_admin_without_wallet_address_uses_own_user_id_when_automation_is_owned(
        self,
        admin_client,
        mock_auth,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_owned_by_caller():
                    response = admin_client.post(
                        "/api/v1/debug/",
                        json=_stop_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        assert mock_execute_user_action.await_args[0][1] == ADMIN_USER_ID

    def test_tenant_can_restart_own_terminal_automation(
        self,
        tenant_client,
        mock_auth,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _terminal_automation_owned_by_caller():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=_restart_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    def test_tenant_can_restart_when_terminal_workflow_has_input_only_state(
        self,
        tenant_client,
        mock_auth,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _terminal_automation_owned_by_caller():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=_restart_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID

    def test_admin_without_wallet_address_uses_terminal_owner_user_id_for_restart(
        self,
        admin_client,
        mock_auth,
    ):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        with mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _terminal_automation_not_owned_by_caller(owner_user_id=TENANT_USER_ID):
                    response = admin_client.post(
                        "/api/v1/debug/",
                        json=_restart_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        assert mock_execute_user_action.await_args[0][1] == TENANT_USER_ID


def _exchange_config_create_user_action_payload() -> dict:
    exchange_config = protocol_models.ExchangeConfig(
        id="extra-exchange-config",
        name="extra",
        exchange="binance",
        sandboxed=False,
    )
    inner = protocol_models.CreateExchangeConfigConfiguration(
        action_type=protocol_models.UserActionType.EXCHANGE_CONFIG_CREATE,
        configuration=exchange_config,
    )
    user_action = protocol_models.UserAction(
        id="ua-demo-exchange-config-create",
        configuration=protocol_models.UserActionConfiguration(inner),
    )
    return json.loads(user_action.to_json())


class TestExecuteUserActionDemoAgentSeedSandbox:
    def test_validates_with_resolved_user_id_before_execute(self, tenant_client, mock_auth):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        real_validate = demo_agent_seed_wallet.validate_demo_agent_seed_user_action
        validate_spy = mock.Mock(wraps=real_validate)
        with mock.patch(
            f"{_DEBUG_ROUTE_MODULE}.demo_agent_seed_wallet.validate_demo_agent_seed_user_action",
            validate_spy,
        ), mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_owned_by_caller():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=_stop_automation_user_action_payload(),
                    )
        assert response.status_code == 204
        validate_spy.assert_called_once()
        validate_user_id, validate_user_action = validate_spy.call_args[0]
        assert validate_user_id == TENANT_USER_ID
        assert validate_user_action.id == "ua-stop-api-test"
        mock_execute_user_action.assert_awaited_once()

    def test_demo_forbidden_returns_403_and_skips_execute(self, tenant_client, mock_auth):
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        forbidden_detail = demo_agent_seed_constants.DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL
        with mock.patch(
            f"{_DEBUG_ROUTE_MODULE}.demo_agent_seed_wallet.validate_demo_agent_seed_user_action",
            side_effect=demo_agent_seed_wallet.DemoAgentSeedUserActionForbiddenError(
                forbidden_detail,
            ),
        ), mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                with _automation_owned_by_caller():
                    response = tenant_client.post(
                        "/api/v1/debug/",
                        json=_stop_automation_user_action_payload(),
                    )
        assert response.status_code == 403
        assert response.json()["detail"] == forbidden_detail
        mock_execute_user_action.assert_not_awaited()

    @mock.patch.object(demo_agent_seed_wallet.community_authentication.CommunityAuthentication, "instance")
    def test_demo_exchange_config_create_returns_403_end_to_end(
        self,
        auth_mock,
        tenant_client,
        mock_auth,
    ):
        wallet_mock = mock.Mock(address=demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_EVM_ADDRESS)
        auth_mock.return_value.get_wallet_by_user_id.return_value = wallet_mock
        auth_mock.return_value.get_wallet_name.return_value = (
            demo_agent_seed_constants.DEMO_AGENT_SEED_WALLET_DISPLAY_NAME
        )
        mock_execute_user_action = mock.AsyncMock(return_value=None)
        mock_resolve_execution_user_id = mock.AsyncMock(
            return_value=demo_agent_seed_constants.DEMO_AGENT_SEED_USER_ID,
        )
        with mock.patch(
            f"{_DEBUG_ROUTE_MODULE}._resolve_execution_user_id",
            new=mock_resolve_execution_user_id,
        ), mock.patch(
            "octobot_node.protocol.user_actions.execute_user_action",
            new=mock_execute_user_action,
        ):
            with mock.patch("octobot_node.scheduler.is_initialized", return_value=True):
                response = tenant_client.post(
                    "/api/v1/debug/",
                    json=_exchange_config_create_user_action_payload(),
                )
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == demo_agent_seed_constants.DEMO_AGENT_SEED_FORBIDDEN_ACTION_DETAIL
        )
        mock_execute_user_action.assert_not_awaited()
