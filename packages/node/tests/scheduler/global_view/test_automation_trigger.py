#  Drakkar-Software OctoBot-Node

import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_node.scheduler.global_view.automation_trigger as automation_trigger_module


def _automation_state(
    automation_id: str,
    *,
    account_id: str,
    order_ids: list[str],
) -> protocol_models.AutomationState:
    return protocol_models.AutomationState(
        id=automation_id,
        status=protocol_models.WorkflowStatus.RUNNING,
        metadata=protocol_models.AutomationMetadata(
            name=automation_id,
            description=automation_id,
        ),
        exchange_account_ids=[account_id],
        orders=[
            protocol_models.OrderSummary(id=order_id, symbol="BTC/USDT")
            for order_id in order_ids
        ],
    )


@pytest.mark.asyncio
class TestAccountHasBoundRunningAutomation:
    async def test_true_when_running_automation_lists_account(self):
        automation = _automation_state(
            "automation-1",
            account_id="acc-1",
            order_ids=["order-1"],
        )
        with mock.patch.object(
            automation_trigger_module,
            "scheduler_api",
        ) as scheduler_api_mock:
            scheduler_api_mock.get_automation_states = mock.AsyncMock(return_value=[automation])
            assert await automation_trigger_module.account_has_bound_running_automation(
                "wallet-1",
                "acc-1",
            ) is True

    async def test_false_when_no_running_automation_for_account(self):
        automation = _automation_state(
            "automation-1",
            account_id="other-acc",
            order_ids=["order-1"],
        )
        with mock.patch.object(
            automation_trigger_module,
            "scheduler_api",
        ) as scheduler_api_mock:
            scheduler_api_mock.get_automation_states = mock.AsyncMock(return_value=[automation])
            assert await automation_trigger_module.account_has_bound_running_automation(
                "wallet-1",
                "acc-1",
            ) is False


@pytest.mark.asyncio
class TestTriggerAccountAutomations:
    async def test_triggers_only_matching_automation_sequentially(self):
        matching_automation = _automation_state(
            "automation-gv-fill",
            account_id="acc-sim-1",
            order_ids=["gv-order-fill-1"],
        )
        non_matching_automation = _automation_state(
            "automation-gv-no-trigger",
            account_id="acc-sim-1",
            order_ids=["gv-order-stays-open"],
        )
        trigger_calls: list[str] = []

        async def _record_trigger(user_id: str, automation_id: str) -> None:
            trigger_calls.append(automation_id)

        with mock.patch.object(
            automation_trigger_module,
            "scheduler_api",
        ) as scheduler_api_mock, mock.patch.object(
            automation_trigger_module,
            "_trigger_automation_and_wait",
            side_effect=_record_trigger,
        ):
            scheduler_api_mock.get_automation_states = mock.AsyncMock(
                return_value=[matching_automation, non_matching_automation],
            )
            await automation_trigger_module.trigger_account_automations(
                "wallet-1",
                "acc-sim-1",
                {"gv-order-fill-1"},
            )
        assert trigger_calls == ["automation-gv-fill"]


@pytest.mark.asyncio
class TestTriggerAutomationAndWait:
    async def test_logs_info_sequence_when_waiting_for_workflow(self):
        import octobot_node.scheduler as scheduler_package

        mock_logger = mock.Mock()
        scheduler = mock.Mock()
        scheduler.resolve_active_automation_workflow_ids_for_parent_id = mock.AsyncMock(
            return_value=["workflow-1"],
        )
        with (
            mock.patch.object(
                scheduler_package,
                "SCHEDULER",
                scheduler,
            ),
            mock.patch.object(
                automation_trigger_module,
                "_logger",
                return_value=mock_logger,
            ),
            mock.patch.object(
                automation_trigger_module.scheduler_tasks,
                "send_forced_trigger_to_active_automation",
                mock.AsyncMock(),
            ) as send_trigger_mock,
            mock.patch.object(
                automation_trigger_module,
                "_wait_for_workflow_iteration_success",
                mock.AsyncMock(),
            ) as wait_mock,
        ):
            await automation_trigger_module._trigger_automation_and_wait(
                "wallet-1",
                "automation-1",
            )

        send_trigger_mock.assert_awaited_once_with("automation-1", "wallet-1")
        wait_mock.assert_awaited_once_with("workflow-1")
        info_messages = [call.args[0] for call in mock_logger.info.call_args_list]
        assert info_messages == [
            "Starting forced automation trigger (automation_id=%s, user_id=%s)",
            "Resolved active workflow before trigger (automation_id=%s, workflow_id=%s)",
            "Forced trigger sent (automation_id=%s, user_id=%s)",
            "Waiting for automation workflow iteration (workflow_id=%s)",
            "Finished waiting for automation workflow iteration (workflow_id=%s)",
        ]
        assert mock_logger.info.call_args_list[0].args[1:] == ("automation-1", "wallet-1")
        assert mock_logger.info.call_args_list[1].args[1:] == ("automation-1", "workflow-1")
        assert mock_logger.info.call_args_list[2].args[1:] == ("automation-1", "wallet-1")
        assert mock_logger.info.call_args_list[3].args[1:] == ("workflow-1",)
        assert mock_logger.info.call_args_list[4].args[1:] == ("workflow-1",)
        mock_logger.warning.assert_not_called()
