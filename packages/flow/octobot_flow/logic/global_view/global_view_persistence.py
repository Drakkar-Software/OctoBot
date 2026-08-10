#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_sync.sync.collection_providers as collection_providers

import octobot_flow.entities
import octobot_flow.logic.accounts.account_state_persistence as account_state_persistence_module


def persist_global_view_refresh_result(
    user_id: str,
    account_id: str,
    refresh_result: octobot_flow.entities.GlobalViewAccountRefreshResult,
) -> None:
    collection_providers.AccountProvider.instance().update_item(user_id, refresh_result.updated_account)
    account_state_persistence_module.persist_account_trading(
        user_id,
        account_id,
        refresh_result.open_orders or [],
        refresh_result.trades or [],
        refresh_result.positions or [],
    )
    if refresh_result.portfolio_history_state is not None:
        collection_providers.AccountHistoryProvider.instance().save_state(
            user_id,
            account_id,
            refresh_result.portfolio_history_state,
        )
