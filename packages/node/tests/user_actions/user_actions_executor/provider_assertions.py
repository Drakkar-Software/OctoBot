#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime
import typing

import octobot_protocol.models as protocol_models

import octobot_node.user_actions.user_actions_provider as user_actions_provider_module

from . import account_executor_test_utils


def assert_provider_user_action_terminal_state(
    *,
    user_action_id: str,
    expected_status: protocol_models.UserActionStatus,
    result_channel: typing.Literal["account", "automation"],
    expect_error_details: bool,
    expected_error_message: typing.Any | None = None,
    wallet_address: str = account_executor_test_utils.WALLET_ADDRESS,
) -> protocol_models.UserAction:
    stored = user_actions_provider_module.UserActionsProvider.instance().get_user_action(
        wallet_address,
        user_action_id,
    )
    assert stored.status == expected_status
    assert stored.created_at is not None
    assert stored.updated_at is not None
    assert stored.updated_at >= stored.created_at
    if stored.created_at.tzinfo is None:
        created = stored.created_at.replace(tzinfo=datetime.UTC)
    else:
        created = stored.created_at
    if stored.updated_at.tzinfo is None:
        updated = stored.updated_at.replace(tzinfo=datetime.UTC)
    else:
        updated = stored.updated_at
    assert updated >= created
    assert stored.result is not None
    inner = stored.result.actual_instance
    if result_channel == "account":
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.ACCOUNT
    else:
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.AUTOMATION
    assert inner.updated_at is not None
    inner_updated = inner.updated_at if inner.updated_at.tzinfo else inner.updated_at.replace(tzinfo=datetime.UTC)
    assert inner_updated >= created
    if expect_error_details:
        assert inner.error_details is not None
        assert len(inner.error_details) > 0
    else:
        assert inner.error_details is None
        assert inner.error_message is None
    if expected_error_message is not None:
        assert inner.error_message == expected_error_message
    return stored
