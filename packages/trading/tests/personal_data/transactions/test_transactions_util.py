#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_trading.enums as enums
import octobot_trading.personal_data.transactions.transactions_util as transactions_util

TXID = enums.ExchangeConstantsTransactionColumns.TXID.value


def _tx(txid, amount="1"):
    return {TXID: txid, "amount": amount}


def test_merge_transactions_deduped_empty_existing_returns_new():
    new = [_tx("a"), _tx("b")]
    assert transactions_util.merge_transactions_deduped([], new) == new


def test_merge_transactions_deduped_empty_new_returns_existing():
    existing = [_tx("a"), _tx("b")]
    assert transactions_util.merge_transactions_deduped(existing, []) == existing


def test_merge_transactions_deduped_appends_only_unseen_txids_in_order():
    existing = [_tx("a"), _tx("b")]
    new = [_tx("c"), _tx("d")]
    assert transactions_util.merge_transactions_deduped(existing, new) == [
        _tx("a"),
        _tx("b"),
        _tx("c"),
        _tx("d"),
    ]


def test_merge_transactions_deduped_skips_txids_already_in_existing():
    existing = [_tx("a", "1"), _tx("b", "2")]
    new = [_tx("b", "999"), _tx("c", "3")]
    merged = transactions_util.merge_transactions_deduped(existing, new)
    assert merged == [_tx("a", "1"), _tx("b", "2"), _tx("c", "3")]


def test_merge_transactions_deduped_keeps_first_occurrence_of_duplicate_in_new():
    new = [_tx("x", "first"), _tx("x", "second")]
    merged = transactions_util.merge_transactions_deduped([], new)
    assert merged == [_tx("x", "first")]


def test_merge_transactions_deduped_does_not_mutate_inputs():
    existing = [_tx("a")]
    new = [_tx("b")]
    transactions_util.merge_transactions_deduped(existing, new)
    assert existing == [_tx("a")]
    assert new == [_tx("b")]
