#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot Node is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import typing

import octobot_commons.constants as commons_constants
import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models


_AUTH_DETAIL_FIELD_NAMES = (
    "api_key",
    "api_secret",
    "api_password",
    "access_token",
    "encrypted",
)

_ACCOUNT_AUTHENTICATION_SENSITIVE_FIELD_NAMES = (
    "api_key",
    "api_secret",
    "api_passphrase",
    "public_key",
    "private_key",
    "seed_phrase",
)


def _auth_details_dict_has_credentials(auth_details: dict) -> bool:
    return bool(
        auth_details.get("api_key")
        or auth_details.get("api_secret")
        or auth_details.get("api_password")
        or auth_details.get("access_token")
        or auth_details.get("encrypted")
    )


def _redact_auth_details_dict(auth_details: dict) -> dict:
    redacted_auth_details = dict(auth_details)
    for field_name in _AUTH_DETAIL_FIELD_NAMES:
        if redacted_auth_details.get(field_name):
            redacted_auth_details[field_name] = commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
    return redacted_auth_details


def _privatize_dag_action(action: protocol_models.Action) -> protocol_models.Action:
    if action.action_type != flow_enums.ActionType.APPLY_CONFIGURATION.value:
        return action
    configuration = action.configuration
    if configuration is None:
        return action
    exchange_account_details = configuration.get("exchange_account_details")
    if not isinstance(exchange_account_details, dict):
        return action
    auth_details = exchange_account_details.get("auth_details")
    if not isinstance(auth_details, dict) or not _auth_details_dict_has_credentials(auth_details):
        return action
    redacted_configuration = {
        **configuration,
        "exchange_account_details": {
            **exchange_account_details,
            "auth_details": _redact_auth_details_dict(auth_details),
        },
    }
    return action.model_copy(update={"configuration": redacted_configuration})


def privatize_dag_actions(
    actions: typing.Optional[list[protocol_models.Action]],
) -> typing.Optional[list[protocol_models.Action]]:
    if actions is None:
        return None
    return [_privatize_dag_action(action) for action in actions]


def _account_authentication_has_credentials(
    authentication: protocol_models.AccountAuthentication,
) -> bool:
    return any(
        getattr(authentication, field_name)
        for field_name in _ACCOUNT_AUTHENTICATION_SENSITIVE_FIELD_NAMES
    )


def _privatize_account_authentication(
    authentication: protocol_models.AccountAuthentication,
) -> protocol_models.AccountAuthentication:
    if not _account_authentication_has_credentials(authentication):
        return authentication
    redacted_updates = {
        field_name: commons_constants.PRIVATE_MESSAGE_PLACEHOLDER
        for field_name in _ACCOUNT_AUTHENTICATION_SENSITIVE_FIELD_NAMES
        if getattr(authentication, field_name)
    }
    return authentication.model_copy(update=redacted_updates)


def privatize_user_action(
    user_action: protocol_models.UserAction,
) -> protocol_models.UserAction:
    configuration = user_action.configuration
    if configuration is None or configuration.actual_instance is None:
        return user_action
    actual_configuration = configuration.actual_instance
    if isinstance(actual_configuration, protocol_models.CreateAccountAuthConfiguration):
        redacted_authentication = _privatize_account_authentication(
            actual_configuration.configuration,
        )
        if redacted_authentication is actual_configuration.configuration:
            return user_action
        redacted_configuration = actual_configuration.model_copy(
            update={"configuration": redacted_authentication},
        )
        return user_action.model_copy(
            update={
                "configuration": protocol_models.UserActionConfiguration(
                    redacted_configuration,
                ),
            },
        )
    if isinstance(actual_configuration, protocol_models.EditAccountAuthConfiguration):
        redacted_authentication = _privatize_account_authentication(
            actual_configuration.configuration,
        )
        if redacted_authentication is actual_configuration.configuration:
            return user_action
        redacted_configuration = actual_configuration.model_copy(
            update={"configuration": redacted_authentication},
        )
        return user_action.model_copy(
            update={
                "configuration": protocol_models.UserActionConfiguration(
                    redacted_configuration,
                ),
            },
        )
    return user_action
