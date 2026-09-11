#  Drakkar-Software OctoBot-Node
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License version 3.0 of the License, or (at your option) any later version.

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.enums as octobot_node_enums
import octobot_node.protocol.user_actions as user_actions_module

_TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def _minimal_user_action(action_identifier: str) -> protocol_models.UserAction:
    configuration_inner = protocol_models.StopAutomationConfiguration(
        id="auto-stop-inner",
        action_type=protocol_models.UserActionType.AUTOMATION_STOP,
    )
    configuration_model = protocol_models.UserActionConfiguration.from_json(configuration_inner.to_json())
    return protocol_models.UserAction(id=action_identifier, configuration=configuration_model)


class Test_execute_user_action:
    """Checks :func:`octobot_node.protocol.user_actions.execute_user_action` delegates to scheduler tasks."""

    @pytest.mark.asyncio
    async def test_calls_trigger_user_action_workflow_with_wallet_and_payload(self):
        user_action_payload = _minimal_user_action(action_identifier="ua-delegate-check")
        with mock.patch.object(
            user_actions_module.scheduler_tasks,
            "trigger_user_action_workflow",
            new_callable=mock.AsyncMock,
        ) as trigger_workflow_mock, mock.patch.object(
            user_actions_module.node_journal,
            "record_external_action_received",
        ):
            await user_actions_module.execute_user_action(user_action_payload, _TEST_WALLET_ADDRESS)
        trigger_workflow_mock.assert_awaited_once_with(user_action_payload, _TEST_WALLET_ADDRESS)

    @pytest.mark.asyncio
    async def test_sync_source_emits_entry_onboarding_milestones(self):
        user_action_payload = _minimal_user_action(action_identifier="ua-entry-check")
        with mock.patch.object(
            user_actions_module.node_journal,
            "record_external_action_received",
        ) as entry_mock, mock.patch.object(
            user_actions_module.scheduler_tasks,
            "trigger_user_action_workflow",
            new_callable=mock.AsyncMock,
        ):
            await user_actions_module.execute_user_action(
                user_action_payload,
                _TEST_WALLET_ADDRESS,
                source=octobot_node_enums.UserActionSource.SYNC,
            )
        entry_mock.assert_called_once_with(
            user_action_payload,
            source=octobot_node_enums.UserActionSource.SYNC.value,
        )

    @pytest.mark.asyncio
    async def test_debug_api_emits_entry_onboarding_milestones_with_source(self):
        user_action_payload = _minimal_user_action(action_identifier="ua-debug-check")
        with mock.patch.object(
            user_actions_module.node_journal,
            "record_external_action_received",
        ) as entry_mock, mock.patch.object(
            user_actions_module.scheduler_tasks,
            "trigger_user_action_workflow",
            new_callable=mock.AsyncMock,
        ):
            await user_actions_module.execute_user_action(
                user_action_payload,
                _TEST_WALLET_ADDRESS,
                source=octobot_node_enums.UserActionSource.DEBUG_API,
            )
        entry_mock.assert_called_once_with(
            user_action_payload,
            source=octobot_node_enums.UserActionSource.DEBUG_API.value,
        )

    @pytest.mark.asyncio
    async def test_surfaces_scheduler_not_initialized_as_runtime_error(self):
        user_action_payload = _minimal_user_action(action_identifier="ua-not-init")
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            with pytest.raises(RuntimeError, match="Scheduler is not initialized"):
                await user_actions_module.execute_user_action(user_action_payload, _TEST_WALLET_ADDRESS)
