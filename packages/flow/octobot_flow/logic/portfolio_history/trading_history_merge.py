import datetime

import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.personal_data.trades.protocol as trades_protocol
import octobot_trading.personal_data.trades.trades_util as trades_util
import octobot_trading.personal_data.transactions.protocol as transactions_protocol
import octobot_trading.personal_data.transactions.transactions_util as transactions_util


def merge_and_persist_trading_history(
    wallet_id: str,
    account_id: str,
    new_trades: list[dict],
    new_transactions: list[dict],
) -> None:
    """
    Merge new trades and transactions into AccountTrading without touching
    orders or positions.
    """
    trading_state = collection_providers.AccountTradingProvider.instance().load_state(
        wallet_id,
        account_id,
    )
    account_trading = trading_state.account_trading

    # Merge trades.
    existing_trade_dicts = [
        trades_protocol.exchange_columns_dict_from_protocol_trade(protocol_trade)
        for protocol_trade in (account_trading.trades or [])
    ]
    merged_trade_dicts = trades_util.merge_trades_deduped(existing_trade_dicts, new_trades)
    account_trading.trades = [
        trades_protocol.to_protocol_trade(trade_dict) for trade_dict in merged_trade_dicts
    ] or None

    # Merge transactions.
    existing_tx_dicts = [
        transactions_protocol.to_exchange_columns_dict(protocol_tx)
        for protocol_tx in (account_trading.transactions or [])
    ]
    merged_tx_dicts = transactions_util.merge_transactions_deduped(existing_tx_dicts, new_transactions)
    account_trading.transactions = [
        transactions_protocol.to_protocol_transaction(tx_dict) for tx_dict in merged_tx_dicts
    ] or None

    account_trading.updated_at = datetime.datetime.now(datetime.UTC)
    collection_providers.AccountTradingProvider.instance().save_state(
        wallet_id,
        account_id,
        trading_state,
    )
