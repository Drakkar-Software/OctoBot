#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.exchange_data as exchange_data_module

import octobot_flow.repositories.exchange.ohlcv_repository as ohlcv_repository_module

pytestmark = pytest.mark.asyncio


class TestOhlcvRepositoryEnsureTemporaryOhlcvChannel:
    async def test_delegates_to_channel_producer_ensure(self):
        exchange_manager = mock.Mock()
        with mock.patch.object(
            ohlcv_repository_module.channel_producer_ensure_module,
            "ensure_temporary_channel_producer",
            mock.AsyncMock(),
        ) as ensure_mock:
            await ohlcv_repository_module.OhlcvRepository.ensure_temporary_ohlcv_channel(exchange_manager)

        ensure_mock.assert_awaited_once_with(
            exchange_manager,
            ohlcv_repository_module.octobot_trading.constants.OHLCV_CHANNEL,
            exchange_data_module.OHLCVUpdater,
        )
