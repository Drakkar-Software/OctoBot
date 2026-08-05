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

import octobot_flow.enums as flow_enums
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module


def protocol_action_configuration(
    configuration: typing.Optional[dict],
    *,
    action_type: str,
) -> typing.Optional[dict]:
    if configuration is None:
        return None
    if action_type != flow_enums.ActionType.APPLY_CONFIGURATION.value:
        return configuration
    exchange_account_details = configuration.get("exchange_account_details")
    if not isinstance(exchange_account_details, dict):
        return configuration
    auth_details = exchange_account_details.get("auth_details")
    if not isinstance(auth_details, dict):
        return configuration
    stripped_auth_details = exchange_data_module.ExchangeAuthDetails.non_credential_dict(
        auth_details,
    )
    if stripped_auth_details == auth_details:
        return configuration
    return {
        **configuration,
        "exchange_account_details": {
            **exchange_account_details,
            "auth_details": stripped_auth_details,
        },
    }


def _protocol_account_authentication(
    authentication: protocol_models.AccountAuthentication,
) -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id=authentication.id,
        updated_at=authentication.updated_at,
    )


def to_protocol_user_action(
    user_action: protocol_models.UserAction,
) -> protocol_models.UserAction:
    configuration = user_action.configuration
    if configuration is None or configuration.actual_instance is None:
        return user_action
    actual_configuration = configuration.actual_instance
    if isinstance(actual_configuration, protocol_models.CreateAccountAuthConfiguration):
        stripped_authentication = _protocol_account_authentication(
            actual_configuration.configuration,
        )
        if stripped_authentication == actual_configuration.configuration:
            return user_action
        stripped_configuration = actual_configuration.model_copy(
            update={"configuration": stripped_authentication},
        )
        return user_action.model_copy(
            update={
                "configuration": protocol_models.UserActionConfiguration(
                    stripped_configuration,
                ),
            },
        )
    if isinstance(actual_configuration, protocol_models.EditAccountAuthConfiguration):
        stripped_authentication = _protocol_account_authentication(
            actual_configuration.configuration,
        )
        if stripped_authentication == actual_configuration.configuration:
            return user_action
        stripped_configuration = actual_configuration.model_copy(
            update={"configuration": stripped_authentication},
        )
        return user_action.model_copy(
            update={
                "configuration": protocol_models.UserActionConfiguration(
                    stripped_configuration,
                ),
            },
        )
    return user_action
