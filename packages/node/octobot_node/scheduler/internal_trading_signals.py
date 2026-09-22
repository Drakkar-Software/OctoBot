import dbos

import octobot_commons.logging
import octobot_flow.entities
import octobot_flow.repositories.community as trading_signals_channel
import octobot_node.enums as octobot_node_enums
import octobot_node.scheduler as scheduler
import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader
import octobot_node.scheduler.tasks as tasks
import octobot_node.scheduler.workflows_util as workflows_util_module


async def _on_internal_trading_signal(trading_signal: octobot_flow.entities.TradingSignal) -> None:
    await _trigger_copier_automation(trading_signal)


async def subscribe_internal_trading_signal_consumer() -> None:
    """
    Propagates trading signals from the internal trading signal channel to running automations.
    Signals can from from a local signal emitter or from send_internal_trading_signal
    """

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
    pending_workflow_statuses = await workflows_util_module.list_scheduler_workflows_async(
        scheduler.SCHEDULER.INSTANCE,
        octobot_node_enums.SchedulerWorkflowNames.EXECUTE_AUTOMATION,
        [
            dbos.WorkflowStatusString.ENQUEUED,
            dbos.WorkflowStatusString.PENDING,
        ],
        None,
        load_output=False,
        load_input=True,
    )
    for pending_workflow_status in pending_workflow_statuses:
        if (
            trading_signal.strategy_id in automation_states_loader.get_automation_copied_strategy_ids(pending_workflow_status)
        ):
            octobot_commons.logging.get_logger("internal_trading_signals").info(
                f"Triggering copier automation {pending_workflow_status.workflow_id} with trading signal {trading_signal.strategy_id}"
            )
            await tasks.trigger_copier_automation(
                pending_workflow_status.workflow_id, trading_signal
            )
