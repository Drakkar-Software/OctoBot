import mock
import pytest

import octobot_flow.repositories.exchange.trades_repository as trades_repository_module
import octobot_trading.personal_data as trading_personal_data


def _make_repo(exchange_manager):
    fetched_data = mock.MagicMock()
    return trades_repository_module.TradesRepository(exchange_manager, [], fetched_data)


class TestTradesRepositoryFetchTrades:
    @pytest.mark.asyncio
    async def test_uses_updater_fetch_and_ensure_parsing(self):
        exchange_manager = mock.MagicMock()
        repo = _make_repo(exchange_manager)
        updater = mock.AsyncMock()
        updater.fetch_trades.return_value = [{"id": "raw-trade-1"}]
        with (
            mock.patch.object(repo, "get_channel_updater", return_value=updater),
            mock.patch.object(
                trading_personal_data.TradesUpdater,
                "ensure_parsing",
                return_value={"id": "parsed-trade-1"},
            ) as ensure_parsing_mock,
        ):
            result = await repo.fetch_trades(["BTC/USDT"])

        updater.fetch_trades.assert_awaited_once_with(["BTC/USDT"])
        ensure_parsing_mock.assert_called_once_with(exchange_manager, {"id": "raw-trade-1"})
        assert result == [{"id": "parsed-trade-1"}]

    @pytest.mark.asyncio
    async def test_empty_symbols_returns_empty_list(self):
        repo = _make_repo(mock.MagicMock())
        assert await repo.fetch_trades([]) == []


class TestTradesRepositoryEnsureTemporaryTradesChannel:
    @pytest.mark.asyncio
    async def test_creates_channels_and_trades_producer_only(self):
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
            await trades_repository_module.TradesRepository.ensure_temporary_trades_channel(exchange_manager)

        create_exchange_channels_mock.assert_awaited_once_with(exchange_manager)
        create_producers_mock.assert_awaited_once_with(
            exchange_manager,
            [trading_personal_data.TradesUpdater],
            start_producers=False,
        )
