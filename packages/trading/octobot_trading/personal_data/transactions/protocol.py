import datetime

import octobot_trading.enums as enums

import octobot_protocol.models as protocol_models


_PROTOCOL_TYPE_TO_TRANSACTION_TYPE = {
    protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT: enums.TransactionType.BLOCKCHAIN_DEPOSIT,
    protocol_models.TransactionType.BLOCKCHAIN_WITHDRAWAL: enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
    protocol_models.TransactionType.FUNDING_FEE: enums.TransactionType.FUNDING_FEE,
    protocol_models.TransactionType.TRADING_FEE: enums.TransactionType.TRADING_FEE,
}

_TRANSACTION_TYPE_TO_PROTOCOL_TYPE = {
    value: key for key, value in _PROTOCOL_TYPE_TO_TRANSACTION_TYPE.items()
}


def to_exchange_columns_dict(protocol_tx: protocol_models.Transaction) -> dict:
    """Convert a protocol Transaction to a dict keyed by ExchangeConstantsTransactionColumns."""
    return {
        enums.ExchangeConstantsTransactionColumns.TXID.value: protocol_tx.id,
        enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: int(protocol_tx.timestamp.timestamp() * 1000),
        enums.ExchangeConstantsTransactionColumns.CURRENCY.value: protocol_tx.asset,
        enums.ExchangeConstantsTransactionColumns.AMOUNT.value: float(protocol_tx.amount),
        enums.ExchangeConstantsTransactionColumns.TYPE.value: _PROTOCOL_TYPE_TO_TRANSACTION_TYPE.get(
            protocol_tx.type, enums.TransactionType.TRANSFER
        ).value,
    }


def to_protocol_transaction(raw: dict) -> protocol_models.Transaction:
    """Convert a raw exchange-columns dict to a protocol Transaction."""
    timestamp_ms = raw.get(enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value, 0)
    tx_type_str = raw.get(enums.ExchangeConstantsTransactionColumns.TYPE.value, "")

    trading_type = None
    for trading_enum_member in enums.TransactionType:
        if trading_enum_member.value == tx_type_str:
            trading_type = trading_enum_member
            break

    protocol_type = _TRANSACTION_TYPE_TO_PROTOCOL_TYPE.get(
        trading_type, protocol_models.TransactionType.BLOCKCHAIN_DEPOSIT
    )

    return protocol_models.Transaction(
        id=raw.get(enums.ExchangeConstantsTransactionColumns.TXID.value, ""),
        timestamp=datetime.datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime.timezone.utc),
        asset=raw.get(enums.ExchangeConstantsTransactionColumns.CURRENCY.value, ""),
        amount=float(raw.get(enums.ExchangeConstantsTransactionColumns.AMOUNT.value, 0)),
        type=protocol_type,
    )
