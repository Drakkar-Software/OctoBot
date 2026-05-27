#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
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


def assert_user_action_terminal_state(
    *,
    user_action: protocol_models.UserAction,
    expected_status: protocol_models.UserActionStatus,
    result_channel: typing.Literal["account", "automation", "exchange_config"],
    expect_error_details: bool,
    expected_error_message: typing.Any | None = None,
) -> protocol_models.UserAction:
    stored = user_action
    assert stored.status == expected_status
    assert stored.result is not None
    inner = stored.result.actual_instance
    if result_channel == "account":
        assert isinstance(inner, protocol_models.AccountActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.ACCOUNT
    elif result_channel == "exchange_config":
        assert isinstance(inner, protocol_models.ExchangeConfigActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.EXCHANGE_CONFIG
    else:
        assert isinstance(inner, protocol_models.AutomationActionResult)
        assert inner.result_type == protocol_models.UserActionResultType.AUTOMATION
    assert inner.updated_at is not None
    inner_updated = inner.updated_at if inner.updated_at.tzinfo else inner.updated_at.replace(tzinfo=datetime.UTC)
    if stored.created_at is not None:
        created = stored.created_at if stored.created_at.tzinfo else stored.created_at.replace(tzinfo=datetime.UTC)
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
