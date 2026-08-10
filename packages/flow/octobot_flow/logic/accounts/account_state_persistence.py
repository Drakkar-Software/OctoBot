#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import datetime

import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.personal_data.orders.protocol as orders_protocol
import octobot_trading.personal_data.positions.protocol as positions_protocol
import octobot_trading.personal_data.trades.protocol as trades_protocol
import octobot_trading.personal_data.trades.trades_util as trades_util

import octobot_flow.logic.accounts.portfolio_history as portfolio_history_module
import octobot_flow.logic.exchange.orders.order_change_detection as order_change_detection_module


def load_previous_open_order_exchange_ids(user_id: str, account_id: str) -> set[str]:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            user_id,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        return set()
    except Exception:
        return set()
    account_trading = trading_state.account_trading
    if account_trading is None or account_trading.orders is None:
        return set()
    return order_change_detection_module.open_order_exchange_ids_from_protocol_orders(
        account_trading.orders
    )


def load_portfolio_history_state(
    user_id: str,
    account_id: str,
) -> protocol_models.PortfolioHistoricalValuesState:
    try:
        return collection_providers.AccountHistoryProvider.instance().load_state(user_id, account_id)
    except collection_errors.CollectionNoDataError:
        return protocol_models.PortfolioHistoricalValuesState(
            version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
            history=None,
        )


def build_portfolio_history_state(
    user_id: str,
    account_id: str,
    snapshot: protocol_models.PortfolioHistoricalValue,
    valuation_unit: str,
    evaluation_time: datetime.datetime,
) -> protocol_models.PortfolioHistoricalValuesState:
    history_state = load_portfolio_history_state(user_id, account_id)
    existing_values = (
        history_state.history.values
        if history_state.history is not None and history_state.history.values
        else []
    )
    merged_values = portfolio_history_module.merge_snapshot(
        existing_values,
        snapshot,
        evaluation_time,
    )
    updated_history = protocol_models.PortfolioHistoricalValues(
        unit=valuation_unit,
        values=merged_values,
    )
    return protocol_models.PortfolioHistoricalValuesState(
        version=sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION,
        history=updated_history,
    )


def persist_account_trading(
    user_id: str,
    account_id: str,
    orders: list[dict],
    trades: list[dict],
    positions: list[dict],
) -> None:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            user_id,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        trading_state = protocol_models.AccountTradingState(
            version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
            account_trading=protocol_models.AccountTrading(
                updated_at=datetime.datetime.now(datetime.UTC),
            ),
        )
    account_trading = trading_state.account_trading
    account_trading.orders = [orders_protocol.to_protocol_order(order) for order in orders] or None
    account_trading.positions = [
        positions_protocol.to_protocol_position(position) for position in positions
    ] or None
    existing_trade_dicts = [
        trades_protocol.exchange_columns_dict_from_protocol_trade(protocol_trade)
        for protocol_trade in (account_trading.trades or [])
    ]
    merged_trade_dicts = trades_util.merge_trades_deduped(existing_trade_dicts, trades)
    account_trading.trades = [
        trades_protocol.to_protocol_trade(trade_dict) for trade_dict in merged_trade_dicts
    ] or None
    account_trading.updated_at = datetime.datetime.now(datetime.UTC)
    collection_providers.AccountTradingProvider.instance().save_state(
        user_id,
        account_id,
        trading_state,
    )
