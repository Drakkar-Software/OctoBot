import octobot_commons.constants as commons_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_module


def _order_stub(exchange_order_id: str, symbol: str = "BTC/USDT") -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_order_id,
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
        }
    }


def _trade_stub(trade_id: str) -> dict:
    trade_id_key = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
    return {trade_id_key: trade_id}


def _tx_stub(txid: str) -> dict:
    txid_key = trading_enums.ExchangeConstantsTransactionColumns.TXID.value
    return {txid_key: txid}


class TestExchangeAccountElementsAggregateSnapshots:
    def test_returns_empty_when_no_snapshots(self):
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots([])
        assert aggregated.name is None
        assert aggregated.portfolio.content == {}
        assert aggregated.orders.open_orders == []

    def test_returns_copy_when_single_snapshot(self):
        snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="binanceus",
            orders=exchange_data_import.OrdersDetails(open_orders=[_order_stub("order-a")]),
        )
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots([snapshot])
        assert aggregated is not snapshot
        assert aggregated.name == "binanceus"
        assert len(aggregated.orders.open_orders) == 1

    def test_merges_portfolios_with_overlapping_and_distinct_assets(self):
        binance_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="binanceus",
            portfolio=exchange_data_import.PortfolioDetails(
                content={
                    "USDT": {
                        commons_constants.PORTFOLIO_TOTAL: 1000.0,
                        commons_constants.PORTFOLIO_AVAILABLE: 900.0,
                    },
                    "BTC": {
                        commons_constants.PORTFOLIO_TOTAL: 0.01,
                        commons_constants.PORTFOLIO_AVAILABLE: 0.01,
                    },
                }
            ),
        )
        okx_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="okx",
            portfolio=exchange_data_import.PortfolioDetails(
                content={
                    "USDT": {
                        commons_constants.PORTFOLIO_TOTAL: 500.0,
                        commons_constants.PORTFOLIO_AVAILABLE: 400.0,
                    },
                    "ETH": {
                        commons_constants.PORTFOLIO_TOTAL: 1.5,
                        commons_constants.PORTFOLIO_AVAILABLE: 1.5,
                    },
                }
            ),
        )
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots(
            [binance_snapshot, okx_snapshot]
        )
        portfolio_content = aggregated.portfolio.content
        assert portfolio_content["USDT"][commons_constants.PORTFOLIO_TOTAL] == 1500.0
        assert portfolio_content["USDT"][commons_constants.PORTFOLIO_AVAILABLE] == 1300.0
        assert portfolio_content["BTC"][commons_constants.PORTFOLIO_TOTAL] == 0.01
        assert portfolio_content["ETH"][commons_constants.PORTFOLIO_TOTAL] == 1.5

    def test_concatenates_orders_from_all_snapshots(self):
        binance_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="binanceus",
            orders=exchange_data_import.OrdersDetails(
                open_orders=[_order_stub("binance-order", "BTC/USDT")],
            ),
        )
        okx_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="okx",
            orders=exchange_data_import.OrdersDetails(
                open_orders=[_order_stub("okx-order", "ETH/USDT")],
            ),
        )
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots(
            [binance_snapshot, okx_snapshot]
        )
        symbols = {
            order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value
            ]
            for order in aggregated.orders.open_orders
        }
        assert symbols == {"BTC/USDT", "ETH/USDT"}

    def test_dedupes_trades_and_transactions_by_id(self):
        first_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="binanceus",
            trades=[_trade_stub("trade-a")],
            transactions=[_tx_stub("tx-a")],
        )
        second_snapshot = exchange_account_elements_module.ExchangeAccountElements(
            name="okx",
            trades=[_trade_stub("trade-a"), _trade_stub("trade-b")],
            transactions=[_tx_stub("tx-a"), _tx_stub("tx-b")],
        )
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots(
            [first_snapshot, second_snapshot]
        )
        trade_id_key = trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value
        txid_key = trading_enums.ExchangeConstantsTransactionColumns.TXID.value
        assert [trade[trade_id_key] for trade in aggregated.trades] == ["trade-a", "trade-b"]
        assert [transaction[txid_key] for transaction in aggregated.transactions] == ["tx-a", "tx-b"]

    def test_sets_sorted_comma_separated_exchange_names(self):
        first_snapshot = exchange_account_elements_module.ExchangeAccountElements(name="okx")
        second_snapshot = exchange_account_elements_module.ExchangeAccountElements(name="binanceus")
        aggregated = exchange_account_elements_module.ExchangeAccountElements.aggregate_snapshots(
            [first_snapshot, second_snapshot]
        )
        assert aggregated.name == "binanceus,okx"
