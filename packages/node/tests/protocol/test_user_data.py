#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.constants as node_constants
import octobot_node.protocol.user_data as user_data_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def _minimal_automation_state(automation_identifier: str) -> protocol_models.AutomationState:
    return protocol_models.AutomationState(
        id=automation_identifier,
        status=protocol_models.TaskStatus.RUNNING,
        metadata=protocol_models.AutomationMetadata(name="test-automation", description="test-description"),
    )


class TestGetUserDataState:
    """Checks :func:`octobot_node.protocol.user_data.get_user_data_state`."""

    @pytest.mark.asyncio
    async def test_calls_scheduler_api_and_returns_user_data_version_with_lists(self):
        automations_payload = [_minimal_automation_state("auto-protocol-check")]
        user_actions_payload = [protocol_models.UserAction(id="ua-protocol-check")]
        with (
            mock.patch.object(
                user_data_module.scheduler_api,
                "get_automation_states",
                new_callable=mock.AsyncMock,
                return_value=automations_payload,
            ) as get_automation_states_mock,
            mock.patch.object(
                user_data_module.scheduler_api,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=user_actions_payload,
            ) as list_user_actions_mock,
        ):
            user_data_state = await user_data_module.get_user_data_state(_TEST_WALLET_ADDRESS)
        get_automation_states_mock.assert_awaited_once_with(_TEST_WALLET_ADDRESS)
        list_user_actions_mock.assert_awaited_once_with(_TEST_WALLET_ADDRESS)
        assert user_data_state.version == node_constants.USER_DATA_STATE_VERSION
        assert user_data_state.automations == automations_payload
        assert user_data_state.user_actions == user_actions_payload
        assert isinstance(user_data_state, protocol_models.UserDataState)

    @pytest.mark.asyncio
    async def test_empty_automations_and_user_actions_when_scheduler_returns_empty(self):
        with (
            mock.patch.object(
                user_data_module.scheduler_api,
                "get_automation_states",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
            mock.patch.object(
                user_data_module.scheduler_api,
                "list_user_actions",
                new_callable=mock.AsyncMock,
                return_value=[],
            ),
        ):
            user_data_state = await user_data_module.get_user_data_state(_TEST_WALLET_ADDRESS)
        assert user_data_state.automations == []
        assert user_data_state.user_actions == []
