#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.exchange_data as exchange_data_module
import octobot_trading.constants as trading_constants

import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module

pytestmark = pytest.mark.asyncio


class TestTickersRepositoryEnsureTemporaryTickerChannel:
    async def test_delegates_to_channel_producer_ensure(self):
        exchange_manager = mock.Mock()
        with mock.patch.object(
            tickers_repository_module.channel_producer_ensure_module,
            "ensure_temporary_channel_producer",
            mock.AsyncMock(),
        ) as ensure_mock:
            await tickers_repository_module.TickersRepository.ensure_temporary_ticker_channel(exchange_manager)

        ensure_mock.assert_awaited_once_with(
            exchange_manager,
            trading_constants.TICKER_CHANNEL,
            exchange_data_module.TickerUpdater,
        )
