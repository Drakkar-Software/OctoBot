#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models

import octobot_node.protocol.util.privacy_filter as privacy_filter


class TestPrivatizeDagActions:
    """Checks :func:`octobot_node.protocol.util.privacy_filter.privatize_dag_actions`."""

    def test_redacts_auth_details_in_apply_configuration_action(self):
        action = protocol_models.Action(
            id="action-1",
            action_type="apply_configuration",
            status=protocol_models.WorkflowStatus.COMPLETED,
            configuration={
                "exchange_account_details": {
                    "auth_details": {
                        "api_key": "secret-key",
                        "api_secret": "secret-secret",
                        "api_password": "secret-pass",
                    },
                },
            },
        )
        privatized_actions = privacy_filter.privatize_dag_actions([action])
        auth_details = privatized_actions[0].configuration[
            "exchange_account_details"
        ]["auth_details"]
        assert auth_details["api_key"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert auth_details["api_secret"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert auth_details["api_password"] == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER

    def test_leaves_non_config_actions_unchanged(self):
        dsl_action = protocol_models.Action(
            id="dsl-1",
            action_type="dsl_script",
            status=protocol_models.WorkflowStatus.COMPLETED,
            dsl='run_octobot_process("acc", {}, [{"api_key": "leak"}])',
        )
        privatized_actions = privacy_filter.privatize_dag_actions([dsl_action])
        returned_action = privatized_actions[0]
        assert returned_action is dsl_action
        assert returned_action.dsl == dsl_action.dsl

    def test_leaves_apply_configuration_without_auth_unchanged(self):
        config_action = protocol_models.Action(
            id="action-1",
            action_type="apply_configuration",
            status=protocol_models.WorkflowStatus.COMPLETED,
            configuration={
                "exchange_account_details": {
                    "auth_details": {},
                },
            },
        )
        privatized_actions = privacy_filter.privatize_dag_actions([config_action])
        returned_action = privatized_actions[0]
        assert returned_action is config_action
        assert returned_action.configuration == config_action.configuration


class TestPrivatizeUserAction:
    """Checks :func:`octobot_node.protocol.util.privacy_filter.privatize_user_action`."""

    def test_redacts_create_account_auth_configuration(self):
        user_action = protocol_models.UserAction(
            id="ua-create-auth",
            configuration=protocol_models.UserActionConfiguration(
                protocol_models.CreateAccountAuthConfiguration(
                    action_type=protocol_models.UserActionType.ACCOUNT_AUTH_CREATE,
                    configuration=protocol_models.AccountAuthentication(
                        id="auth-1",
                        api_key="secret-key",
                        api_secret="secret-secret",
                        api_passphrase="secret-pass",
                        public_key="secret-public",
                        private_key="secret-private",
                        seed_phrase="secret-seed",
                    ),
                ),
            ),
        )
        privatized_user_action = privacy_filter.privatize_user_action(user_action)
        authentication = (
            privatized_user_action.configuration.actual_instance.configuration
        )
        assert authentication.api_key == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.api_secret == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.api_passphrase == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.public_key == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.private_key == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.seed_phrase == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.id == "auth-1"

    def test_redacts_edit_account_auth_configuration(self):
        user_action = protocol_models.UserAction(
            id="ua-edit-auth",
            configuration=protocol_models.UserActionConfiguration(
                protocol_models.EditAccountAuthConfiguration(
                    action_type=protocol_models.UserActionType.ACCOUNT_AUTH_EDIT,
                    id="auth-1",
                    configuration=protocol_models.AccountAuthentication(
                        id="auth-1",
                        api_key="secret-key",
                        api_secret="secret-secret",
                    ),
                ),
            ),
        )
        privatized_user_action = privacy_filter.privatize_user_action(user_action)
        authentication = (
            privatized_user_action.configuration.actual_instance.configuration
        )
        assert authentication.api_key == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.api_secret == commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        assert authentication.id == "auth-1"

    def test_leaves_non_account_auth_user_actions_unchanged(self):
        stop_user_action = protocol_models.UserAction(
            id="ua-stop",
            configuration=protocol_models.UserActionConfiguration(
                protocol_models.StopAutomationConfiguration(
                    action_type=protocol_models.UserActionType.AUTOMATION_STOP,
                    id="auto-1",
                ),
            ),
        )
        privatized_user_action = privacy_filter.privatize_user_action(stop_user_action)
        assert privatized_user_action is stop_user_action
