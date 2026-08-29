import octobot_trading.enums as octobot_trading_enums_import

import octobot_flow.entities as octobot_flow_entities


def _trade_dict(trade_id: str, symbol: str, timestamp: float) -> dict:
    order_columns = octobot_trading_enums_import.ExchangeConstantsOrderColumns
    return {
        order_columns.EXCHANGE_TRADE_ID.value: trade_id,
        order_columns.SYMBOL.value: symbol,
        order_columns.TIMESTAMP.value: timestamp,
    }


class TestTrimTradesToLiveWindow:
    def test_keeps_newest_trades_and_archives_older_ids_by_symbol(self):
        elements = octobot_flow_entities.ExchangeAccountElements(
            trades=[
                _trade_dict("old-1", "BTC/USDT", 1.0),
                _trade_dict("new-1", "ETH/USDT", 3.0),
                _trade_dict("old-2", "BTC/USDT", 2.0),
            ]
        )
        elements.trim_trades_to_live_window(2)
        trade_id_key = octobot_trading_enums_import.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
        kept_trade_ids = [trade[trade_id_key] for trade in elements.trades]
        assert kept_trade_ids == ["old-2", "new-1"]
        assert elements.trade_summaries == {"BTC/USDT": ["old-1"]}

    def test_deduplicates_archived_ids_per_symbol(self):
        elements = octobot_flow_entities.ExchangeAccountElements(
            trades=[
                _trade_dict("old-1", "BTC/USDT", 1.0),
                _trade_dict("old-2", "BTC/USDT", 2.0),
            ],
            trade_summaries={"BTC/USDT": ["old-1"]},
        )
        elements.trim_trades_to_live_window(1)
        assert elements.trade_summaries == {"BTC/USDT": ["old-1"]}
        assert len(elements.trades) == 1

    def test_no_op_when_trade_count_within_window(self):
        elements = octobot_flow_entities.ExchangeAccountElements(
            trades=[_trade_dict("trade-1", "BTC/USDT", 1.0)],
            trade_summaries={"ETH/USDT": ["archived-1"]},
        )
        elements.trim_trades_to_live_window(100)
        assert len(elements.trades) == 1
        assert elements.trade_summaries == {"ETH/USDT": ["archived-1"]}

    def test_skips_evicted_trade_missing_symbol(self):
        order_columns = octobot_trading_enums_import.ExchangeConstantsOrderColumns
        elements = octobot_flow_entities.ExchangeAccountElements(
            trades=[
                {
                    order_columns.EXCHANGE_TRADE_ID.value: "no-symbol",
                    order_columns.TIMESTAMP.value: 1.0,
                },
                _trade_dict("keep-1", "BTC/USDT", 2.0),
            ]
        )
        elements.trim_trades_to_live_window(1)
        assert len(elements.trades) == 1
        assert elements.trades[0][order_columns.EXCHANGE_TRADE_ID.value] == "keep-1"
        assert elements.trade_summaries == {}


class TestExchangeAccountElementsTradeSummariesRoundTrip:
    def test_to_dict_from_dict_preserves_trade_summaries_dict(self):
        elements = octobot_flow_entities.ExchangeAccountElements(
            trade_summaries={"BTC/USDT": ["archived-1", "archived-2"]},
        )
        restored = octobot_flow_entities.ExchangeAccountElements.from_dict(
            elements.to_dict(include_default_values=False)
        )
        assert restored.trade_summaries == {"BTC/USDT": ["archived-1", "archived-2"]}
