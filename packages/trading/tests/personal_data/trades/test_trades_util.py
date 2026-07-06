#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.

import octobot_trading.enums as trading_enums
import octobot_trading.personal_data.trades.trades_util as trades_util_module

_ORDER_COLUMNS = trading_enums.ExchangeConstantsOrderColumns


class TestTradeIdentityKey:
    """Checks :func:`octobot_trading.personal_data.trades.trades_util.trade_identity_key`."""

    def test_prefers_exchange_trade_id(self):
        trade = {
            _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-99",
            _ORDER_COLUMNS.EXCHANGE_ID.value: "order-1",
        }
        assert trades_util_module.trade_identity_key(trade) == (
            _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value,
            "trade-99",
        )

    def test_falls_back_to_exchange_id(self):
        trade = {_ORDER_COLUMNS.EXCHANGE_ID.value: "order-42"}
        assert trades_util_module.trade_identity_key(trade) == (
            _ORDER_COLUMNS.EXCHANGE_ID.value,
            "order-42",
        )

    def test_prefers_id_over_exchange_id_when_exchange_trade_id_missing(self):
        trade = {
            _ORDER_COLUMNS.ID.value: "local-trade-1",
            _ORDER_COLUMNS.EXCHANGE_ID.value: "exchange-order-9",
        }
        assert trades_util_module.trade_identity_key(trade) == (
            _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value,
            "local-trade-1",
        )

    def test_normalizes_numeric_identity_values_to_str(self):
        trade = {_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: 12345}
        assert trades_util_module.trade_identity_key(trade) == (
            _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value,
            "12345",
        )

    def test_returns_none_when_no_identity_fields(self):
        assert trades_util_module.trade_identity_key({}) is None


class TestMergeTradesDeduped:
    """Checks :func:`octobot_trading.personal_data.trades.trades_util.merge_trades_deduped`."""

    def test_appends_new_trades_by_exchange_trade_id(self):
        existing = [{_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-a"}]
        incoming = [{_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-b"}]
        merged = trades_util_module.merge_trades_deduped(existing, incoming)
        assert len(merged) == 2

    def test_skips_duplicate_exchange_trade_id(self):
        existing = [{_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-a"}]
        incoming = [{_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-a"}]
        merged = trades_util_module.merge_trades_deduped(existing, incoming)
        assert len(merged) == 1

    def test_skips_incoming_trades_without_identity(self):
        existing = [{_ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: "trade-a"}]
        incoming = [{"symbol": "BTC/USDT"}]
        merged = trades_util_module.merge_trades_deduped(existing, incoming)
        assert len(merged) == 1

    def test_skips_duplicate_after_protocol_round_trip_identity(self):
        local_trade_id = "local-trade-1"
        existing = [
            {
                _ORDER_COLUMNS.EXCHANGE_TRADE_ID.value: local_trade_id,
                _ORDER_COLUMNS.EXCHANGE_ID.value: local_trade_id,
                _ORDER_COLUMNS.ID.value: local_trade_id,
            }
        ]
        incoming = [
            {
                _ORDER_COLUMNS.ID.value: local_trade_id,
                _ORDER_COLUMNS.EXCHANGE_ID.value: "exchange-order-9",
            }
        ]
        merged = trades_util_module.merge_trades_deduped(existing, incoming)
        assert len(merged) == 1

    def test_repeated_merge_with_same_incoming_full_trade_list(self):
        local_trade_id = "local-trade-2"
        incoming = [
            {
                _ORDER_COLUMNS.ID.value: local_trade_id,
                _ORDER_COLUMNS.EXCHANGE_ID.value: "exchange-order-10",
                _ORDER_COLUMNS.SYMBOL.value: "BTC/USDT",
            }
        ]
        merged_once = trades_util_module.merge_trades_deduped([], incoming)
        merged_twice = trades_util_module.merge_trades_deduped(merged_once, incoming)
        assert len(merged_twice) == 1
