#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_flow.jobs.exchange_account_job as exchange_account_job_module

TICKER_WISE_SELF_PAIR = "USDT@ETH/USDT@ETH"
STABLE_TO_STABLE_PAIR = "USDC/USDT"
TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


def _exchange_account_job_for_tickers() -> exchange_account_job_module.ExchangeAccountJob:
    job = exchange_account_job_module.ExchangeAccountJob(mock.Mock(), [])
    job._exchange_manager = mock.Mock()
    job._exchange_manager.exchange_name = "coinrabbit"
    job.fetched_dependencies = mock.Mock()
    job.fetched_dependencies.fetched_exchange_data.public_data.tickers = {}
    return job


class TestExchangeAccountJobFetchTickers:
    @pytest.mark.asyncio
    async def test_filters_non_fetchable_symbols_before_repository_call(self):
        job = _exchange_account_job_for_tickers()
        job._get_traded_symbols = mock.Mock(
            return_value=[TICKER_WISE_SELF_PAIR, STABLE_TO_STABLE_PAIR, TICKER_WISE_SYMBOL],
        )
        tickers_repository = mock.Mock()
        tickers_repository.fetch_tickers = mock.AsyncMock(return_value={})
        repository_factory = mock.Mock()
        repository_factory.get_tickers_repository.return_value = tickers_repository
        job.get_exchange_repository_factory = mock.Mock(return_value=repository_factory)

        await job._fetch_tickers()

        tickers_repository.fetch_tickers.assert_awaited_once_with([TICKER_WISE_SYMBOL])
