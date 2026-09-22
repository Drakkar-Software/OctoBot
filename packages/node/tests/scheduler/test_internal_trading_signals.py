import asyncio
import time

import dbos
import mock
import pytest

import async_channel.channels as async_channel_channels

pytest.importorskip("octobot_flow")

import octobot_flow.entities as flow_entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.trading_signals_repository as trading_signals_repository
import octobot_node.scheduler.internal_trading_signals as internal_trading_signals
import octobot_copy.constants as copy_constants
import octobot_protocol.models as protocol_models


def _channel_name() -> str:
    return trading_signals_channel.InternalTradingSignalChannel.get_name()


@pytest.mark.asyncio
async def test_subscribe_internal_trading_signal_consumer_registers_consumer():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    channel = async_channel_channels.get_chan(_channel_name())
    assert len(channel.get_consumers()) >= 1
    await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_shutdown_internal_trading_signal_channel_after_subscribe_unregisters():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    with pytest.raises(KeyError):
        async_channel_channels.get_chan(_channel_name())


@pytest.mark.asyncio
async def test_get_or_create_after_shutdown_creates_new_channel():
    async_channel_channels.del_chan(_channel_name())
    await internal_trading_signals.subscribe_internal_trading_signal_consumer()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    new_channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert new_channel is not None
    await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_trigger_copier_automation_lists_pending_automation_workflows_by_name():
    pending_workflow_status = mock.Mock(workflow_id="automation-wf-1")
    list_pending_mock = mock.AsyncMock(return_value=[pending_workflow_status])
    signal = flow_entities.TradingSignal(
        account=protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=time.time(),
            copied_assets=[],
        ),
        strategy_id="test-strategy-id",
    )
    with (
        mock.patch.object(
            internal_trading_signals,
            "list_pending_copier_automation_workflow_statuses",
            list_pending_mock,
        ),
        mock.patch(
            "octobot_node.scheduler.automations.automation_states_loader.get_automation_copied_strategy_ids",
            return_value=set(),
        ),
        mock.patch(
            "octobot_node.scheduler.tasks.trigger_copier_automation",
            mock.AsyncMock(),
        ) as trigger_copier_automation_mock,
    ):
        await internal_trading_signals._trigger_copier_automation(signal)

    list_pending_mock.assert_awaited_once()
    trigger_copier_automation_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_trigger_copier_automation_triggers_all_matching_pending_children():
    pending_child_one = mock.Mock(workflow_id="automation-wf-1")
    pending_child_two = mock.Mock(workflow_id="automation-wf-2")
    list_pending_mock = mock.AsyncMock(return_value=[pending_child_one, pending_child_two])
    signal = flow_entities.TradingSignal(
        account=protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=time.time(),
            copied_assets=[],
        ),
        strategy_id="test-strategy-id",
    )
    with (
        mock.patch.object(
            internal_trading_signals,
            "list_pending_copier_automation_workflow_statuses",
            list_pending_mock,
        ),
        mock.patch(
            "octobot_node.scheduler.automations.automation_states_loader.get_automation_copied_strategy_ids",
            return_value={"test-strategy-id"},
        ),
        mock.patch(
            "octobot_node.scheduler.tasks.trigger_copier_automation",
            mock.AsyncMock(),
        ) as trigger_copier_automation_mock,
    ):
        await internal_trading_signals._trigger_copier_automation(signal)

    assert trigger_copier_automation_mock.await_count == 2
    triggered_workflow_ids = [
        call.args[0] for call in trigger_copier_automation_mock.await_args_list
    ]
    assert triggered_workflow_ids == ["automation-wf-1", "automation-wf-2"]


@pytest.mark.asyncio
async def test_insert_trading_signal_completes_without_error_after_subscribe():
    async_channel_channels.del_chan(_channel_name())
    with (
        mock.patch.object(
            internal_trading_signals,
            "_trigger_copier_automation",
            mock.AsyncMock(),
        ) as trigger_copier_automation_mock,
        mock.patch.object(
            trading_signals_repository.TradingSignalsRepository,
            "_upload_trading_signal",
            mock.AsyncMock(),
        ) as upload_trading_signal_mock,
    ):
        await internal_trading_signals.subscribe_internal_trading_signal_consumer()
        signal = flow_entities.TradingSignal(
            account=protocol_models.CopiedAccount(
                version=copy_constants.COPIED_ACCOUNT_VERSION,
                updated_at=time.time(),
                copied_assets=[],
            ),
            strategy_id="test-strategy-id",
        )
        repository = trading_signals_repository.TradingSignalsRepository(object())  # type: ignore[arg-type]
        await repository.insert_trading_signal(signal)
        upload_trading_signal_mock.assert_called_once_with(signal)
        await asyncio.sleep(0.05)
        trigger_copier_automation_mock.assert_called_once_with(signal)
        await trading_signals_channel.shutdown_internal_trading_signal_channel()
