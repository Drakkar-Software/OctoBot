#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.exchange_data as exchange_data_module

import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module

pytestmark = pytest.mark.asyncio


class TestTickersRepositoryEnsureTemporaryTickerChannel:
    async def test_creates_channels_and_ticker_producer_only(self):
        exchange_manager = mock.Mock()
        with (
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
        ):
            await tickers_repository_module.TickersRepository.ensure_temporary_ticker_channel(exchange_manager)

        create_exchange_channels_mock.assert_awaited_once_with(exchange_manager)
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [exchange_data_module.TickerUpdater],
            start_producers=False,
        )
