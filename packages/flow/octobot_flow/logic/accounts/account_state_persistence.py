#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import datetime
import typing

import octobot_commons.logging as octobot_commons_logging
import octobot.community.wallet_backend.errors as wallet_backend_errors
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.orders.protocol as orders_protocol
import octobot_trading.personal_data.positions.protocol as positions_protocol
import octobot_trading.personal_data.trades.protocol as trades_protocol
import octobot_trading.personal_data.trades.trades_util as trades_util
import octobot_trading.personal_data.transactions.protocol as transactions_protocol
import octobot_trading.personal_data.transactions.transactions_util as transactions_util

import octobot_flow.entities
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
    account_trading = trading_state.account_trading
    if account_trading is None or account_trading.orders is None:
        return set()
    return order_change_detection_module.open_order_exchange_ids_from_protocol_orders(
        account_trading.orders
    )


def load_previous_open_orders(user_id: str, account_id: str) -> list[dict]:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            user_id,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        return []
    account_trading = trading_state.account_trading
    if account_trading is None or account_trading.orders is None:
        return []
    return [
        {
            trading_constants.STORAGE_ORIGIN_VALUE: orders_protocol.exchange_columns_dict_from_protocol_order(
                protocol_order
            ),
        }
        for protocol_order in account_trading.orders
    ]


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


def _normalize_order_for_protocol(order: dict) -> dict:
    order_details = order.get(trading_constants.STORAGE_ORIGIN_VALUE, order)
    order_id = order_details.get(trading_enums.ExchangeConstantsOrderColumns.ID.value)
    exchange_id = order_details.get(trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value)
    if not order_id:
        if exchange_id:
            order_details[trading_enums.ExchangeConstantsOrderColumns.ID.value] = exchange_id
        else:
            raise ValueError(
                f"Order is missing both id and exchange_id: {sorted(order_details.keys())}"
            )
    return order


def persist_account_trading(
    user_id: str,
    account_id: str,
    orders: list[dict],
    trades: list[dict],
    positions: list[dict],
    transactions: list[dict] | None = None,
) -> None:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            user_id,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        # Abnormal: AccountTradingState must be created with the account, not invent here.
        raise
    account_trading = trading_state.account_trading
    account_trading.orders = [
        orders_protocol.to_protocol_order(_normalize_order_for_protocol(order))
        for order in orders
    ] or None
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
    if transactions is not None:
        existing_tx_dicts = [
            transactions_protocol.to_exchange_columns_dict(protocol_tx)
            for protocol_tx in (account_trading.transactions or [])
        ]
        merged_tx_dicts = transactions_util.merge_transactions_deduped(existing_tx_dicts, transactions)
        account_trading.transactions = [
            transactions_protocol.to_protocol_transaction(tx_dict) for tx_dict in merged_tx_dicts
        ] or None
    account_trading.updated_at = datetime.datetime.now(datetime.UTC)
    collection_providers.AccountTradingProvider.instance().save_state(
        user_id,
        account_id,
        trading_state,
    )


def persist_account_trading_orders(
    user_id: str,
    account_id: str,
    orders: list[dict],
) -> None:
    try:
        trading_state = collection_providers.AccountTradingProvider.instance().load_state(
            user_id,
            account_id,
        )
    except collection_errors.CollectionNoDataError:
        # Abnormal: AccountTradingState must be created with the account, not invent here.
        raise
    account_trading = trading_state.account_trading
    account_trading.orders = [
        orders_protocol.to_protocol_order(_normalize_order_for_protocol(order))
        for order in orders
    ] or None
    account_trading.updated_at = datetime.datetime.now(datetime.UTC)
    collection_providers.AccountTradingProvider.instance().save_state(
        user_id,
        account_id,
        trading_state,
    )


def persist_account_trading_from_iteration_state(
    user_id: typing.Optional[str],
    iteration_state: typing.Optional[dict],
) -> None:
    if user_id is None or iteration_state is None:
        return
    automation_state = octobot_flow.entities.AutomationState.from_dict(iteration_state)
    exchange_account_elements = automation_state.automation.exchange_account_elements
    exchange_account_details = automation_state.exchange_account_details
    if exchange_account_elements is None or exchange_account_details is None:
        return
    exchange_account_id = exchange_account_details.exchange_details.exchange_account_id
    if not exchange_account_id:
        return
    try:
        persist_account_trading(
            user_id,
            exchange_account_id,
            list(exchange_account_elements.orders.open_orders),
            list(exchange_account_elements.trades),
            [
                position_details.position
                for position_details in exchange_account_elements.positions
            ],
        )
    except wallet_backend_errors.WalletNotFoundError:
        # Trading collections are wallet-scoped; skip until the wallet is registered locally.
        octobot_commons_logging.get_logger(__name__).warning(
            "Skipping account trading persistence for wallet %s: wallet not registered",
            user_id,
        )


def trim_live_trades_in_iteration_state(
    iteration_state: typing.Optional[dict],
    max_full_trades: int,
) -> None:
    if iteration_state is None or max_full_trades <= 0:
        return
    automation_state = octobot_flow.entities.AutomationState.from_dict(iteration_state)
    exchange_account_elements = automation_state.automation.exchange_account_elements
    if exchange_account_elements is None:
        return
    exchange_account_elements.trim_trades_to_live_window(max_full_trades)
    trimmed_state = automation_state.to_dict(include_default_values=False)
    iteration_state.clear()
    iteration_state.update(trimmed_state)
