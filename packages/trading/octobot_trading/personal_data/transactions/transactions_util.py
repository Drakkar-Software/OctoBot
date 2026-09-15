import octobot_trading.enums as enums


def merge_transactions_deduped(
    existing: list[dict],
    new: list[dict],
) -> list[dict]:
    """
    Merge new transaction dicts into existing, deduplicating by TXID.
    Preserves ordering of existing, appends truly new entries at the end.
    """
    seen_txids: set[str] = set()
    for transaction in existing:
        if txid := transaction.get(enums.ExchangeConstantsTransactionColumns.TXID.value):
            seen_txids.add(txid)

    merged = list(existing)
    for transaction in new:
        if txid := transaction.get(enums.ExchangeConstantsTransactionColumns.TXID.value):
            if txid in seen_txids:
                continue
            merged.append(transaction)
            seen_txids.add(txid)

    return merged
