#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_trading.errors as trading_errors

import octobot_flow.entities
import octobot_flow.jobs.exchange_account_job as exchange_account_job_module


def _exchange_context_job() -> exchange_account_job_module.ExchangeAccountJob:
    job = exchange_account_job_module.ExchangeAccountJob(mock.Mock(), [])
    job._exchange_manager = mock.Mock()
    job._exchange_manager.exchange_name = "binanceus"
    job.profile_data_provider.get_profile_data = mock.Mock(
        return_value=mock.Mock(trader_simulator=mock.Mock(enabled=False)),
    )
    return job


class TestExchangeAccountJobFetchTradesFromOrders:
    @pytest.mark.asyncio
    async def test_fetches_trades_for_order_symbols(self):
        job = _exchange_context_job()
        orders = exchange_data_import.OrdersDetails(
            open_orders=[
                {
                    trading_constants.STORAGE_ORIGIN_VALUE: {
                        trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDC",
                    },
                },
            ],
        )
        trades_repository = mock.Mock()
        trades_repository.fetch_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1", "symbol": "BTC/USDC"}],
        )
        repository_factory = mock.Mock()
        repository_factory.get_trades_repository.return_value = trades_repository
        job.get_exchange_repository_factory = mock.Mock(return_value=repository_factory)

        trades = await exchange_account_job_module.ExchangeAccountJob.fetch_trades_from_orders(
            job,
            orders,
        )

        trades_repository.fetch_trades.assert_awaited_once_with(["BTC/USDC"])
        assert trades == [{"id": "trade-1", "symbol": "BTC/USDC"}]

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_order_symbols(self):
        job = _exchange_context_job()
        job.get_exchange_repository_factory = mock.Mock()

        trades = await exchange_account_job_module.ExchangeAccountJob.fetch_trades_from_orders(
            job,
            exchange_data_import.OrdersDetails(),
        )

        job.get_exchange_repository_factory.assert_not_called()
        assert trades == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_simulator_enabled(self):
        job = _exchange_context_job()
        job.profile_data_provider.get_profile_data = mock.Mock(
            return_value=mock.Mock(trader_simulator=mock.Mock(enabled=True)),
        )
        job.get_exchange_repository_factory = mock.Mock()
        orders = exchange_data_import.OrdersDetails(
            open_orders=[{"symbol": "BTC/USDC"}],
        )

        trades = await exchange_account_job_module.ExchangeAccountJob.fetch_trades_from_orders(
            job,
            orders,
        )

        job.get_exchange_repository_factory.assert_not_called()
        assert trades == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_fetch_not_supported(self):
        job = _exchange_context_job()
        trades_repository = mock.Mock()
        trades_repository.fetch_trades = mock.AsyncMock(
            side_effect=trading_errors.NotSupported("not supported"),
        )
        repository_factory = mock.Mock()
        repository_factory.get_trades_repository.return_value = trades_repository
        job.get_exchange_repository_factory = mock.Mock(return_value=repository_factory)
        orders = exchange_data_import.OrdersDetails(
            open_orders=[{"symbol": "BTC/USDC"}],
        )

        trades = await exchange_account_job_module.ExchangeAccountJob.fetch_trades_from_orders(
            job,
            orders,
        )

        assert trades == []


class TestExchangeAccountJobFetchTrades:
    @pytest.mark.asyncio
    async def test_fetch_trades_populates_fetched_data_from_order_symbols(self):
        automation_state = mock.Mock()
        automation_state.automation.exchange_account_elements = octobot_flow.entities.ExchangeAccountElements(
            orders=exchange_data_import.OrdersDetails(
                missing_orders=[
                    {
                        trading_constants.STORAGE_ORIGIN_VALUE: {
                            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDC",
                        },
                    },
                ],
            ),
        )
        job = exchange_account_job_module.ExchangeAccountJob(automation_state, [])
        job._exchange_manager = mock.Mock()
        job._exchange_manager.exchange_name = "binanceus"
        job.profile_data_provider.get_profile_data = mock.Mock(
            return_value=mock.Mock(trader_simulator=mock.Mock(enabled=False)),
        )
        fetched_data = octobot_flow.entities.FetchedExchangeAccountElements(
            orders=exchange_data_import.OrdersDetails(
                open_orders=[
                    {
                        trading_constants.STORAGE_ORIGIN_VALUE: {
                            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: "BTC/USDC",
                        },
                    },
                ],
            ),
        )
        trades_repository = mock.Mock()
        trades_repository.fetch_trades = mock.AsyncMock(
            return_value=[{"id": "trade-1", "symbol": "BTC/USDC"}],
        )
        repository_factory = mock.Mock()
        repository_factory.get_trades_repository.return_value = trades_repository
        job.get_exchange_repository_factory = mock.Mock(return_value=repository_factory)

        await job._fetch_trades(fetched_data)

        trades_repository.fetch_trades.assert_awaited_once_with(["BTC/USDC"])
        assert len(fetched_data.trades) == 1

    @pytest.mark.asyncio
    async def test_fetch_trades_skips_when_no_order_symbols(self):
        automation_state = mock.Mock()
        automation_state.automation.exchange_account_elements = None
        job = exchange_account_job_module.ExchangeAccountJob(automation_state, [])
        fetched_data = octobot_flow.entities.FetchedExchangeAccountElements()
        job.get_exchange_repository_factory = mock.Mock()

        await job._fetch_trades(fetched_data)

        job.get_exchange_repository_factory.assert_not_called()
        assert fetched_data.trades == []
