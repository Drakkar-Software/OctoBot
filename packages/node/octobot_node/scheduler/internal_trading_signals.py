import dbos

import octobot_commons.logging
import octobot_flow.entities
import octobot_flow.repositories.community as trading_signals_channel
import octobot_node.scheduler.workflows_util as workflows_util
import octobot_node.scheduler.tasks as tasks


async def subscribe_internal_trading_signal_consumer() -> None:
    """
    Propagates trading signals from the internal trading signal channel to running automations.
    Signals can from from a local signal emitter or from send_internal_trading_signal
    """
    async def _on_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
        await _trigger_copier_automation(trading_signal)

    channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await channel.new_consumer(_on_internal_trading_signal)


async def send_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    """
    Broadcasts a trading signal to the internal trading signal channel.
    """
    await trading_signals_channel.send_internal_trading_signal(trading_signal)

async def _trigger_copier_automation(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    """
    Triggers copier automations with the given trading signal.
    Automations are triggered one by one to avoid concurrent executions.
    """
    import octobot_node.scheduler as scheduler
    pending_workflow_statuses = await scheduler.SCHEDULER.INSTANCE.list_workflows_async(
        status=[dbos.WorkflowStatusString.ENQUEUED.value, dbos.WorkflowStatusString.PENDING.value]
    )
    for pending_workflow_status in pending_workflow_statuses:
        if (
            trading_signal.strategy_id in workflows_util.get_automation_copied_strategy_ids(pending_workflow_status)
        ):
            octobot_commons.logging.get_logger("internal_trading_signals").info(
                f"Triggering copier automation {pending_workflow_status.workflow_id} with trading signal {trading_signal.strategy_id}"
            )
            await tasks.trigger_copier_automation(
                pending_workflow_status.workflow_id, trading_signal
            )
