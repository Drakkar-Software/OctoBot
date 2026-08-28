import asyncio
import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.jobs.portfolio_history_job as portfolio_history_job_module
import octobot_flow.repositories.exchange.trades_repository as trades_repository_module

def _make_account(account_id: str, is_simulated: bool = False, is_exchange: bool = True):
    account = mock.MagicMock()
    account.id = account_id
    account.is_simulated = is_simulated
    if is_exchange:
        account.specifics.actual_instance = mock.MagicMock(spec=protocol_models.ExchangeAccount)
    else:
        account.specifics.actual_instance = mock.MagicMock(spec=protocol_models.GenericAccount)
    return account


def _make_context(account, exchange_config=None, trade_symbols=None):
    if exchange_config is None:
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "binance"
        exchange_config.sandboxed = False
        exchange_config.id = "cfg-1"
        exchange_config.name = "binance-main"
        exchange_config.historical_trade_symbols = ["BTC/USDT"]
    if trade_symbols is None:
        trade_symbols = ["BTC/USDT"]
    return portfolio_history_entities.PortfolioHistoryAccountContext(
        account=account,
        exchange_account=account.specifics.actual_instance,
        exchange_config=exchange_config,
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=mock.MagicMock(),
        trade_symbols=list(trade_symbols),
    )


class TestRunForAccountSkipsUnsupported:
    @pytest.mark.asyncio
    async def test_skips_generic_account(self):
        account = _make_account("acc1", is_exchange=False)
        context = _make_context(account)
        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()
        assert results[0].skipped is True
        assert results[0].exchange_name == "binance"

    @pytest.mark.asyncio
    async def test_skips_simulated_account(self):
        account = _make_account("acc1", is_simulated=True)
        context = _make_context(account)
        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()
        assert results[0].skipped is True
        assert results[0].exchange_name == "binance"


class TestRunForAccountDoesNotPersistHistory:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_account_history_provider_not_called(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []
        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        assert not results[0].skipped
        assert results[0].exchange_name == "binance"
        assert results[0].trading_type == protocol_models.TradingType.SPOT.value
        assert results[0].duration_seconds is not None
        assert results[0].duration_seconds >= 0
        assert results[0].price_symbols_count >= 0
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel.assert_awaited_once_with(
            mock_exchange_manager,
        )
        # merge_and_persist_trading_history should be called, but not AccountHistoryProvider
        mock_merge.merge_and_persist_trading_history.assert_called_once()


class TestFetchAndPersistTransactionCurrencies:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_passes_currencies_with_balance_to_tx_repo(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        btc_asset = mock.MagicMock(symbol="BTC", total=1.0)
        eth_asset = mock.MagicMock(symbol="ETH", total=0.5)
        account.assets = [mock.MagicMock(assets=[btc_asset, eth_asset])]
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []
        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        assert not results[0].skipped
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits.assert_awaited_once_with(
            currencies=["BTC", "ETH"]
        )
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals.assert_awaited_once_with(
            currencies=["BTC", "ETH"]
        )

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_skips_tx_fetch_when_no_balance(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        account.assets = []
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []
        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        assert not results[0].skipped
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits.assert_not_awaited()
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals.assert_not_awaited()


class TestFetchTradesUsesContextTradeSymbols:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_fetch_trades_uses_context_trade_symbols(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        context = _make_context(account, trade_symbols=["ETH/USDT"])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["ETH/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        fetch_trades_paginated_mock = mock.AsyncMock(return_value=[])
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = fetch_trades_paginated_mock
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        fetch_trades_paginated_mock.assert_awaited_once()
        assert fetch_trades_paginated_mock.await_args.args[0] == ["ETH/USDT"]
        assert results[0].trade_symbols_count == 1

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_empty_trade_symbols_skips_trade_fetch(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        context = _make_context(account, trade_symbols=[])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = []
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        fetch_trades_paginated_mock = mock.AsyncMock(return_value=[])
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = fetch_trades_paginated_mock
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        fetch_trades_paginated_mock.assert_awaited_once()
        assert fetch_trades_paginated_mock.await_args.args[0] == []
        assert results[0].trade_symbols_count == 0


class TestRunParallelExchangeAccounts:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_multiple_accounts_run_in_parallel(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account1 = _make_account("acc1")
        account2 = _make_account("acc2")
        context1 = _make_context(account1)
        context2 = _make_context(account2)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []
        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context1, context2])
        results = await job.run()

        assert len(results) == 2
        assert mock_merge.merge_and_persist_trading_history.call_count == 2


class TestReferenceMarketFromAccountAssets:
    def test_uses_dominant_usd_like_holding(self):
        account = mock.MagicMock()
        usdc_asset = mock.MagicMock(symbol="USDC", total=402.0)
        usdt_asset = mock.MagicMock(symbol="USDT", total=10.0)
        account.assets = [mock.MagicMock(assets=[usdc_asset, usdt_asset])]

        reference_market = portfolio_history_job_module._reference_market_from_account_assets(
            account,
            "kraken",
        )

        assert reference_market == "USDC"

    def test_falls_back_to_exchange_default_when_no_usd_like_holdings(self):
        account = mock.MagicMock()
        account.assets = []
        with mock.patch(
            "octobot_trading.api.exchange.get_default_exchange_reference_market",
            return_value="USDT",
        ) as default_reference_market_mock:
            reference_market = portfolio_history_job_module._reference_market_from_account_assets(
                account,
                "kraken",
            )

        default_reference_market_mock.assert_called_once_with("kraken")
        assert reference_market == "USDT"


class TestCurrenciesWithBalanceFromAccount:
    def test_returns_sorted_symbols_above_threshold(self):
        account = mock.MagicMock()
        btc_asset = mock.MagicMock(symbol="BTC", total=1.0)
        eth_asset = mock.MagicMock(symbol="ETH", total=0.5)
        usdc_dust_asset = mock.MagicMock(symbol="USDC", total=1e-10)
        account.assets = [mock.MagicMock(assets=[btc_asset, eth_asset, usdc_dust_asset])]

        currencies = portfolio_history_job_module._currencies_with_balance_from_account(account)

        assert currencies == ["BTC", "ETH"]

    def test_returns_empty_when_no_assets(self):
        account = mock.MagicMock()
        account.assets = None

        currencies = portfolio_history_job_module._currencies_with_balance_from_account(account)

        assert currencies == []

    def test_merges_totals_across_trading_types(self):
        account = mock.MagicMock()
        btc_spot_asset = mock.MagicMock(symbol="BTC", total=0.5)
        btc_margin_asset = mock.MagicMock(symbol="BTC", total=1.5)
        account.assets = [
            mock.MagicMock(assets=[btc_spot_asset]),
            mock.MagicMock(assets=[btc_margin_asset]),
        ]

        currencies = portfolio_history_job_module._currencies_with_balance_from_account(account)

        assert currencies == ["BTC"]


class TestDerivePriceSymbols:
    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_skips_reference_market_currency_from_transactions(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            [],
            [{"currency": "USDT"}],
            "USDT",
        )
        assert symbols == []

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_adds_transaction_currency_against_reference_market(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            [],
            [{"currency": "BTC"}],
            "USDT",
        )
        assert symbols == ["BTC/USDT"]

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_filters_invalid_same_base_quote_symbols(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            ["BTC/BTC", "ETH/USDT"],
            [],
            "USDT",
        )
        assert symbols == ["BTC/USDT", "ETH/USDT"]

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_maps_trade_symbols_to_one_reference_pair_per_base(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            ["DOT/BTC", "DOT/EUR", "DOT/USDC", "ETH/BTC"],
            [],
            "USDC",
        )
        assert symbols == ["DOT/USDC", "ETH/USDC"]

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_maps_transaction_currency_to_reference_pair(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            [],
            [{"currency": "EUR"}],
            "USDC",
        )
        assert symbols == ["EUR/USDC"]

    @mock.patch(
        "octobot_trading.api.exchange.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_skips_usd_like_stablecoin_from_transactions(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            [],
            [{"currency": "USDC"}],
            "USDT",
        )
        assert symbols == []


class TestFilterTradesOnLiveMarkets:
    def test_keeps_trades_on_live_markets(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.client_symbols = ["BTC/USDT", "ETH/USDT"]
        trades = [
            {"symbol": "BTC/USDT"},
            {"symbol": "ETH/USDT"},
        ]

        kept_trades, dropped_symbols = portfolio_history_job_module._filter_trades_on_live_markets(
            exchange_manager,
            trades,
        )

        assert kept_trades == trades
        assert dropped_symbols == set()

    def test_drops_trades_on_unknown_or_delisted_markets(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.client_symbols = ["BTC/USDT"]
        trades = [
            {"symbol": "BTC/USDT"},
            {"symbol": "MATICXBT"},
            {"symbol": "FTMEUR"},
        ]

        kept_trades, dropped_symbols = portfolio_history_job_module._filter_trades_on_live_markets(
            exchange_manager,
            trades,
        )

        assert kept_trades == [{"symbol": "BTC/USDT"}]
        assert dropped_symbols == {"FTMEUR", "MATICXBT"}

    def test_drops_trades_with_missing_symbol(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.client_symbols = ["BTC/USDT"]
        trades = [
            {"symbol": "BTC/USDT"},
            {"side": "buy"},
        ]

        kept_trades, dropped_symbols = portfolio_history_job_module._filter_trades_on_live_markets(
            exchange_manager,
            trades,
        )

        assert kept_trades == [{"symbol": "BTC/USDT"}]
        assert dropped_symbols == set()


class TestFilterSymbolsOnLiveMarkets:
    def test_keeps_only_symbols_present_in_client_markets(self):
        exchange_manager = mock.MagicMock()
        exchange_manager.client_symbols = ["BTC/USDT", "ETH/USDT"]

        filtered_symbols = portfolio_history_job_module._filter_symbols_on_live_markets(
            exchange_manager,
            ["BTC/USDT", "MATICXBT", "ETH/USDT", "FTMEUR"],
        )

        assert filtered_symbols == ["BTC/USDT", "ETH/USDT"]


class TestDropDelistedTradesFromJob:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.logger")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_drops_delisted_trades_and_logs_symbols(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers, mock_logger,
    ):
        account = _make_account("acc1")
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "kraken"
        exchange_config.sandboxed = False
        exchange_config.id = "kraken-main"
        exchange_config.name = "kraken-main"
        exchange_config.historical_trade_symbols = []
        context = _make_context(account, exchange_config=exchange_config, trade_symbols=[])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = [
            "BTC/USDC", "MATICXBT", "FTMEUR",
        ]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = {"BTC/USDC"}
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = ["BTC/USDC"]

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDC"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(
            return_value=[
                {"symbol": "BTC/USDC"},
                {"symbol": "MATICXBT"},
                {"symbol": "FTMEUR"},
            ],
        )
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        mock_merge.merge_and_persist_trading_history.assert_called_once_with(
            "wallet1",
            account.id,
            [{"symbol": "BTC/USDC"}],
            [],
        )
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.assert_called_once_with(
            "wallet1",
            exchange_config,
            {"BTC/USDC"},
        )
        info_messages = " ".join(str(argument) for call in mock_logger.info.call_args_list for argument in call.args)
        assert "Dropped" in info_messages
        assert "delisted/unknown markets" in info_messages
        assert "2" in info_messages
        assert "FTMEUR" in info_messages
        assert "MATICXBT" in info_messages


class TestDiscoverAndFetchTradeSymbols:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_discovers_portfolio_symbols_beyond_config_seeds(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "kraken"
        exchange_config.sandboxed = False
        exchange_config.id = "kraken-spot-config"
        exchange_config.name = "kraken-spot-config"
        exchange_config.historical_trade_symbols = ["SOL/USDC"]
        context = _make_context(account, exchange_config=exchange_config, trade_symbols=["SOL/USDC"])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["ALGO/USDC", "KNC/USDC", "SOL/USDC"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        fetch_trades_paginated_mock = mock.AsyncMock(return_value=[])
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = fetch_trades_paginated_mock
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        assert set(fetch_trades_paginated_mock.await_args.args[0]) == {
            "ALGO/USDC", "KNC/USDC", "SOL/USDC",
        }
        assert results[0].trade_symbols_count == 3

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_fetches_deposits_before_trades(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        btc_asset = mock.MagicMock(symbol="BTC", total=1.0)
        account.assets = [mock.MagicMock(assets=[btc_asset])]
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        call_order: list[str] = []

        async def fetch_deposits(**_kwargs):
            call_order.append("deposits")
            return []

        async def fetch_withdrawals(**_kwargs):
            call_order.append("withdrawals")
            return []

        async def fetch_trades_paginated(*_args, **_kwargs):
            call_order.append("trades")
            return []

        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = fetch_trades_paginated
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = fetch_deposits
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = fetch_withdrawals
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        assert call_order.index("deposits") < call_order.index("trades")
        assert call_order.index("withdrawals") < call_order.index("trades")

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.repositories.exchange.trades_repository.logger")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_logs_new_symbol_fetch_at_info(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers, mock_trades_logger,
    ):
        account = _make_account("acc1")
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "kraken"
        exchange_config.sandboxed = False
        exchange_config.id = "kraken-spot-config"
        exchange_config.name = "kraken-spot-config"
        exchange_config.historical_trade_symbols = []
        context = _make_context(account, exchange_config=exchange_config, trade_symbols=[])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["ALGO/USDC"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.MagicMock()
        mock_exchange_manager.client_symbols = ["ALGO/USDC"]
        mock_exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(return_value=[])
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.side_effect = (
            lambda exchange_manager, *_args, **_kwargs: (
                trades_repository_module.TradesRepository(exchange_manager, [], mock.MagicMock())
            )
        )
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        info_messages = " ".join(str(argument) for call in mock_trades_logger.info.call_args_list for argument in call.args)
        assert "Fetching trade history for new symbol" in info_messages
        assert "ALGO/USDC" in info_messages

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.repositories.exchange.trades_repository.logger")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_does_not_log_new_symbol_for_configured_symbol(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers, mock_trades_logger,
    ):
        account = _make_account("acc1")
        context = _make_context(account, trade_symbols=["BTC/USDT"])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["BTC/USDT"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = set()
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = []

        mock_exchange_manager = mock.MagicMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchange_manager.exchange.get_my_recent_trades = mock.AsyncMock(return_value=[])
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.side_effect = (
            lambda exchange_manager, *_args, **_kwargs: (
                trades_repository_module.TradesRepository(exchange_manager, [], mock.MagicMock())
            )
        )
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        info_messages = " ".join(str(call.args[0]) for call in mock_trades_logger.info.call_args_list)
        assert "Fetching trade history for new symbol" not in info_messages


class TestPersistTradeConfirmedConfigFromJob:
    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_persists_only_trade_confirmed_symbols(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "kraken"
        exchange_config.sandboxed = False
        exchange_config.id = "kraken-spot-config"
        exchange_config.name = "kraken-spot-config"
        exchange_config.historical_trade_symbols = []
        context = _make_context(account, exchange_config=exchange_config, trade_symbols=["SOL/USDC"])
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["ALGO/USDC", "GLMR/USDC", "SOL/USDC"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = {"ALGO/USDC"}
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = ["ALGO/USDC"]

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["ALGO/USDC", "GLMR/USDC", "SOL/USDC"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(
            return_value=[{"symbol": "ALGO/USDC"}],
        )
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.assert_called_once_with(
            "wallet1",
            exchange_config,
            {"ALGO/USDC"},
        )

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.logger")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_logs_added_symbols_at_info(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers, mock_logger,
    ):
        account = _make_account("acc1")
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = ["ALGO/USDC"]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = {"ALGO/USDC"}
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = ["ALGO/USDC"]

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        await job.run()

        info_messages = " ".join(str(argument) for call in mock_logger.info.call_args_list for argument in call.args)
        assert "Added trade-confirmed symbols" in info_messages
        assert "ALGO/USDC" in info_messages

    @pytest.mark.asyncio
    @mock.patch("octobot_flow.jobs.portfolio_history_job.collection_providers")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trade_symbols_discovery_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_exchanges")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.tentacles_manager_api")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trading_history_merge_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.daily_price_cache_updater_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.trades_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.transactions_repository_module")
    @mock.patch("octobot_flow.jobs.portfolio_history_job.profile_data_factory_module")
    async def test_trade_symbols_count_reflects_discovered_set(
        self, mock_profile, mock_tx_repo, mock_trades_repo,
        mock_daily_cache, mock_merge, mock_tentacles, mock_exchanges,
        mock_discovery, mock_collection_providers,
    ):
        account = _make_account("acc1")
        context = _make_context(account)
        mock_collection_providers.AccountTradingProvider.instance.return_value.load_state.side_effect = (
            collection_errors.CollectionNoDataError
        )
        mock_discovery.discover_trade_symbols.return_value = [
            "ALGO/USDC", "GLMR/USDC", "KNC/USDC", "SOL/USDC", "STRK/USDC",
        ]
        mock_discovery.trade_confirmed_symbols_from_fetched_trades.return_value = {
            "ALGO/USDC", "KNC/USDC", "SOL/USDC",
        }
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.return_value = [
            "ALGO/USDC", "KNC/USDC", "SOL/USDC",
        ]

        mock_exchange_manager = mock.AsyncMock()
        mock_exchange_manager.client_symbols = ["BTC/USDT"]
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades_paginated = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context])
        results = await job.run()

        assert results[0].trade_symbols_count == 5
        mock_discovery.persist_trade_confirmed_symbols_to_exchange_config.assert_called_once_with(
            "wallet1",
            context.exchange_config,
            {"ALGO/USDC", "KNC/USDC", "SOL/USDC"},
        )
