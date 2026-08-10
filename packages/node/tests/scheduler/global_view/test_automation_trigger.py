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
