import datetime
import mock
import pytest

import octobot_trading.enums as trading_enums

import octobot_flow.logic.portfolio_history.trading_history_merge as trading_history_merge_module


class TestMergeAndPersistTradingHistory:
    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    def test_merges_new_trades_deduped(self, mock_provider_cls):
        mock_provider = mock.MagicMock()
        mock_provider_cls.instance.return_value = mock_provider
        existing_trade = mock.MagicMock()
        existing_trade.trades = []
        existing_trade.transactions = []
        mock_state = mock.MagicMock()
        mock_state.account_trading = existing_trade
        mock_provider.load_state.return_value = mock_state

        new_trades = [
            {
                trading_enums.ExchangeConstantsOrderColumns.ID.value: "t1",
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_TRADE_ID.value: "t1",
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDT",
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: "limit",
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value: "buy",
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: 1.0,
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value: 30000.0,
                trading_enums.ExchangeConstantsOrderColumns.STATUS.value: "filled",
                trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: 1700000000.0,
            }
        ]
        trading_history_merge_module.merge_and_persist_trading_history(
            "wallet1", "acc1", new_trades, [],
        )
        mock_provider.save_state.assert_called_once()

    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    def test_merges_new_transactions_deduped(self, mock_provider_cls):
        mock_provider = mock.MagicMock()
        mock_provider_cls.instance.return_value = mock_provider
        existing_trading = mock.MagicMock()
        existing_trading.trades = []
        existing_trading.transactions = []
        mock_state = mock.MagicMock()
        mock_state.account_trading = existing_trading
        mock_provider.load_state.return_value = mock_state

        new_txs = [
            {
                trading_enums.ExchangeConstantsTransactionColumns.TXID.value: "tx1",
                trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value: "BTC",
                trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value: 1.0,
                trading_enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: 1000000,
                trading_enums.ExchangeConstantsTransactionColumns.TYPE.value: "blockchain_deposit",
            }
        ]
        trading_history_merge_module.merge_and_persist_trading_history(
            "wallet1", "acc1", [], new_txs,
        )
        mock_provider.save_state.assert_called_once()

    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    def test_empty_inputs_still_saves(self, mock_provider_cls):
        mock_provider = mock.MagicMock()
        mock_provider_cls.instance.return_value = mock_provider
        existing_trading = mock.MagicMock()
        existing_trading.trades = []
        existing_trading.transactions = []
        mock_state = mock.MagicMock()
        mock_state.account_trading = existing_trading
        mock_provider.load_state.return_value = mock_state

        trading_history_merge_module.merge_and_persist_trading_history(
            "wallet1", "acc1", [], [],
        )
        mock_provider.save_state.assert_called_once()
