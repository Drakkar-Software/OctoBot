import datetime

import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums

import octobot_flow.logic.portfolio_history.trade_symbols_discovery as trade_symbols_discovery_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


def _exchange_trade(symbol: str, trade_id: str = "trade-1") -> dict:
    order_columns = trading_enums.ExchangeConstantsOrderColumns
    return {
        order_columns.SYMBOL.value: symbol,
        order_columns.ID.value: trade_id,
    }


class TestTradeConfirmedSymbolsFromFetchedTrades:
    def test_returns_unique_symbols_with_trades(self):
        trades = [
            _exchange_trade("ALGO/USDC", "trade-1"),
            _exchange_trade("ALGO/USDC", "trade-2"),
            _exchange_trade("SOL/USDC", "trade-3"),
        ]
        result = trade_symbols_discovery_module.trade_confirmed_symbols_from_fetched_trades(trades)
        assert result == {"ALGO/USDC", "SOL/USDC"}

    def test_returns_empty_set_for_no_trades(self):
        assert trade_symbols_discovery_module.trade_confirmed_symbols_from_fetched_trades([]) == set()

    def test_ignores_trades_without_symbol(self):
        order_columns = trading_enums.ExchangeConstantsOrderColumns
        trades = [{order_columns.ID.value: "trade-1"}]
        assert trade_symbols_discovery_module.trade_confirmed_symbols_from_fetched_trades(trades) == set()


class TestPersistTradeConfirmedSymbolsToExchangeConfig:
    def _exchange_config(self, historical_trade_symbols: list[str] | None) -> protocol_models.ExchangeConfig:
        return protocol_models.ExchangeConfig(
            id="cfg-1",
            name="kraken-spot-config",
            exchange="kraken",
            sandboxed=False,
            historical_trade_symbols=historical_trade_symbols,
        )

    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    def test_updates_config_when_new_trade_symbols(self, account_provider_class):
        account_provider = mock.MagicMock()
        account_provider_class.instance.return_value = account_provider
        existing_config = self._exchange_config(["SOL/USDC"])
        account_provider.get_exchange_config.return_value = existing_config

        result = trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            "wallet-1",
            existing_config,
            {"SOL/USDC", "ALGO/USDC"},
        )

        account_provider.update_exchange_config.assert_called_once()
        updated_config = account_provider.update_exchange_config.call_args.args[1]
        assert updated_config.historical_trade_symbols == ["ALGO/USDC", "SOL/USDC"]
        assert result == ["ALGO/USDC"]

    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    def test_skips_update_when_no_new_symbols(self, account_provider_class):
        account_provider = mock.MagicMock()
        account_provider_class.instance.return_value = account_provider
        existing_config = self._exchange_config(["SOL/USDC"])

        result = trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            "wallet-1",
            existing_config,
            {"SOL/USDC"},
        )

        account_provider.get_exchange_config.assert_not_called()
        account_provider.update_exchange_config.assert_not_called()
        assert result == []

    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    def test_does_not_add_portfolio_only_symbol_without_trades(self, account_provider_class):
        account_provider = mock.MagicMock()
        account_provider_class.instance.return_value = account_provider
        existing_config = self._exchange_config([])

        result = trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            "wallet-1",
            existing_config,
            set(),
        )

        account_provider.update_exchange_config.assert_not_called()
        assert result == []

    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    def test_reloads_config_before_update(self, account_provider_class):
        account_provider = mock.MagicMock()
        account_provider_class.instance.return_value = account_provider
        existing_config = self._exchange_config([])
        account_provider.get_exchange_config.return_value = existing_config

        trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            "wallet-1",
            existing_config,
            {"ALGO/USDC"},
        )

        account_provider.get_exchange_config.assert_called_once_with("wallet-1", "cfg-1")
        account_provider.update_exchange_config.assert_called_once()

    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    def test_merges_sorted_unique_historical_trade_symbols(self, account_provider_class):
        account_provider = mock.MagicMock()
        account_provider_class.instance.return_value = account_provider
        existing_config = self._exchange_config(["BTC/USDC"])
        account_provider.get_exchange_config.return_value = existing_config

        trade_symbols_discovery_module.persist_trade_confirmed_symbols_to_exchange_config(
            "wallet-1",
            existing_config,
            {"ALGO/USDC", "BTC/USDC"},
        )

        updated_config = account_provider.update_exchange_config.call_args.args[1]
        assert updated_config.historical_trade_symbols == ["ALGO/USDC", "BTC/USDC"]
