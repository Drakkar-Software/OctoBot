#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers

import octobot_flow.entities as flow_entities

import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader_module
import octobot_node.scheduler.user_actions.user_actions_executor.util.exchange_account_resolver as exchange_account_resolver


async def resolve_trade_symbols(
    wallet_id: str,
    account: protocol_models.Account,
    exchange_config: protocol_models.ExchangeConfig,
    *,
    automation_states: list[protocol_models.AutomationState] | None = None,
    flow_automation_states_by_id: dict[str, flow_entities.AutomationState] | None = None,
) -> list[str]:
    """Union explicit config symbols with running automation order and strategy pairs."""
    symbols: set[str] = set(exchange_config.historical_trade_symbols or [])
    if automation_states is None or flow_automation_states_by_id is None:
        wallet_automation_states = await automation_states_loader_module.load_wallet_automation_states(wallet_id)
        if automation_states is None:
            automation_states = wallet_automation_states.protocol_states
        if flow_automation_states_by_id is None:
            flow_automation_states_by_id = wallet_automation_states.flow_states_by_id
    for automation_state in automation_states:
        if automation_state.status != protocol_models.WorkflowStatus.RUNNING:
            continue
        if account.id not in (automation_state.exchange_account_ids or []):
            continue
        for order in automation_state.orders or []:
            if order.symbol:
                symbols.add(order.symbol)
        flow_automation_state = flow_automation_states_by_id.get(automation_state.id)
        if flow_automation_state is None:
            continue
        symbols.update(
            _strategy_symbols_from_flow_automation(wallet_id, flow_automation_state)
        )
    return sorted(symbols)


def _strategy_symbols_from_flow_automation(
    wallet_id: str,
    flow_automation_state: flow_entities.AutomationState,
) -> list[str]:
    strategy_id = flow_automation_state.automation.metadata.strategy_id
    if not strategy_id:
        return []
    try:
        stored_strategy = collection_providers.StrategyProvider.instance().get_item(
            wallet_id,
            strategy_id,
        )
    except collection_errors.ItemNotFoundError:
        return []
    configuration_wrapper = stored_strategy.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return []
    inner_configuration = configuration_wrapper.actual_instance
    try:
        return exchange_account_resolver._strategy_traded_symbols(
            inner_configuration,
            reference_market=stored_strategy.reference_market,
        )
    except Exception:
        return []
