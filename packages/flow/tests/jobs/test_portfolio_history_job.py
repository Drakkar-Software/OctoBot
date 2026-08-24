import asyncio
import mock
import pytest

import octobot_protocol.models as protocol_models

import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.jobs.portfolio_history_job as portfolio_history_job_module


def _make_account(account_id: str, is_simulated: bool = False, is_exchange: bool = True):
    account = mock.MagicMock()
    account.id = account_id
    account.is_simulated = is_simulated
    if is_exchange:
        account.specifics.actual_instance = mock.MagicMock(spec=protocol_models.ExchangeAccount)
    else:
        account.specifics.actual_instance = mock.MagicMock(spec=protocol_models.GenericAccount)
    return account


def _make_context(account, exchange_config=None):
    if exchange_config is None:
        exchange_config = mock.MagicMock(spec=protocol_models.ExchangeConfig)
        exchange_config.exchange = "binance"
        exchange_config.sandboxed = False
        exchange_config.historical_trade_symbols = ["BTC/USDT"]
    return portfolio_history_entities.PortfolioHistoryAccountContext(
        account=account,
        exchange_account=account.specifics.actual_instance,
        exchange_config=exchange_config,
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=mock.MagicMock(),
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
    ):
        account = _make_account("acc1")
        context = _make_context(account)

        mock_exchange_manager = mock.AsyncMock()
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades = mock.AsyncMock(return_value=[])
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


class TestRunParallelExchangeAccounts:
    @pytest.mark.asyncio
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
    ):
        account1 = _make_account("acc1")
        account2 = _make_account("acc2")
        context1 = _make_context(account1)
        context2 = _make_context(account2)

        mock_exchange_manager = mock.AsyncMock()
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aenter__ = mock.AsyncMock(
            return_value=mock_exchange_manager
        )
        mock_exchanges.exchange_manager_from_exchange_data.return_value.__aexit__ = mock.AsyncMock(
            return_value=False
        )
        mock_trades_repo.TradesRepository.ensure_temporary_trades_channel = mock.AsyncMock()
        mock_trades_repo.TradesRepository.return_value.fetch_trades = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_deposits = mock.AsyncMock(return_value=[])
        mock_tx_repo.TransactionsRepository.return_value.fetch_withdrawals = mock.AsyncMock(return_value=[])
        mock_daily_cache.update_daily_prices = mock.AsyncMock()

        job = portfolio_history_job_module.PortfolioHistoryJob("wallet1", [context1, context2])
        results = await job.run()

        assert len(results) == 2
        assert mock_merge.merge_and_persist_trading_history.call_count == 2


class TestDerivePriceSymbols:
    @mock.patch(
        "octobot_flow.jobs.portfolio_history_job.scripting_library.get_default_exchange_reference_market",
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
        "octobot_flow.jobs.portfolio_history_job.scripting_library.get_default_exchange_reference_market",
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
        "octobot_flow.jobs.portfolio_history_job.scripting_library.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_filters_invalid_same_base_quote_symbols(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            ["BTC/BTC", "ETH/USDT"],
            [],
            "USDT",
        )
        assert symbols == ["ETH/USDT"]

    @mock.patch(
        "octobot_flow.jobs.portfolio_history_job.scripting_library.get_default_exchange_reference_market",
        return_value="USDT",
    )
    def test_skips_usd_like_stablecoin_from_transactions(self, _mock_reference_market):
        symbols = portfolio_history_job_module._derive_price_symbols(
            [],
            [{"currency": "USDC"}],
            "USDT",
        )
        assert symbols == []
