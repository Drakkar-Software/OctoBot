#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import octobot_protocol.models as protocol_models

import octobot_node.protocol.util.privacy_filter as privacy_filter


class TestProtocolActionConfiguration:
    """Checks :func:`octobot_node.protocol.util.privacy_filter.protocol_action_configuration`."""

    def test_omits_auth_details_credentials_in_apply_configuration(self):
        configuration = {
            "exchange_account_details": {
                "auth_details": {
                    "api_key": "secret-key",
                    "api_secret": "secret-secret",
                    "api_password": "secret-pass",
                    "access_token": "secret-token",
                    "encrypted": "secret-encrypted",
                    "exchange_type": "spot",
                    "sandboxed": True,
                },
            },
        }
        stripped_configuration = privacy_filter.protocol_action_configuration(
            configuration,
            action_type="apply_configuration",
        )
        auth_details = stripped_configuration["exchange_account_details"]["auth_details"]
        assert "api_key" not in auth_details
        assert "api_secret" not in auth_details
        assert "api_password" not in auth_details
        assert "access_token" not in auth_details
        assert "encrypted" not in auth_details
        assert auth_details["exchange_type"] == "spot"
        assert auth_details["sandboxed"] is True

    def test_leaves_non_apply_configuration_configuration_unchanged(self):
        configuration = {
            "exchange_account_details": {
                "auth_details": {
                    "api_key": "secret-key",
                },
            },
        }
        stripped_configuration = privacy_filter.protocol_action_configuration(
            configuration,
            action_type="dsl_script",
        )
        assert stripped_configuration is configuration

    def test_leaves_apply_configuration_without_auth_details_unchanged(self):
        configuration = {
            "exchange_account_details": {
                "auth_details": {},
            },
        }
        stripped_configuration = privacy_filter.protocol_action_configuration(
            configuration,
            action_type="apply_configuration",
        )
        assert stripped_configuration is configuration


class TestToProtocolUserAction:
    """Checks :func:`octobot_node.protocol.util.privacy_filter.to_protocol_user_action`."""

    def test_omits_credentials_from_create_account_auth_configuration(self):
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
        protocol_user_action = privacy_filter.to_protocol_user_action(user_action)
        authentication = (
            protocol_user_action.configuration.actual_instance.configuration
        )
        assert authentication.id == "auth-1"
        assert authentication.api_key is None
        assert authentication.api_secret is None
        assert authentication.api_passphrase is None
        assert authentication.public_key is None
        assert authentication.private_key is None
        assert authentication.seed_phrase is None

    def test_omits_credentials_from_edit_account_auth_configuration(self):
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
        protocol_user_action = privacy_filter.to_protocol_user_action(user_action)
        authentication = (
            protocol_user_action.configuration.actual_instance.configuration
        )
        assert authentication.id == "auth-1"
        assert authentication.api_key is None
        assert authentication.api_secret is None

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
        protocol_user_action = privacy_filter.to_protocol_user_action(stop_user_action)
        assert protocol_user_action is stop_user_action
