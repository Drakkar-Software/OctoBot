#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_flow.entities
import octobot_flow.repositories.exchange.ohlcv_repository as ohlcv_repository_module
import octobot_flow.repositories.exchange.orders_repository as orders_repository_module
import octobot_flow.repositories.exchange.portfolio_repository as portfolio_repository_module
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module
import octobot_flow.repositories.exchange.trades_repository as trades_repository_module

pytestmark = pytest.mark.asyncio


def _fetched_exchange_data():
    return octobot_flow.entities.FetchedExchangeData()


class TestFetchWiringDependencyShapedManager:
    async def test_fetch_methods_no_op_ensure_when_producer_already_present(self):
        exchange_manager = mock.Mock()
        exchange_manager.id = "exchange-manager-1"
        with (
            mock.patch.object(
                trades_repository_module.channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=True,
            ),
            mock.patch.object(
                trades_repository_module.channel_producer_ensure_module,
                "channel_has_producer",
                return_value=True,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(),
            ) as create_exchange_channels_mock,
            mock.patch.object(
                trades_repository_module.TradesRepository,
                "_get_trades_updater",
                return_value=mock.AsyncMock(fetch_trades=mock.AsyncMock(return_value=[])),
            ),
            mock.patch.object(
                tickers_repository_module.TickersRepository,
                "get_channel_updater",
                return_value=mock.AsyncMock(fetch_all_tickers=mock.AsyncMock(return_value={})),
            ),
            mock.patch.object(
                orders_repository_module.OrdersRepository,
                "get_channel_updater",
                return_value=mock.AsyncMock(fetch_open_orders=mock.AsyncMock(return_value=[])),
            ),
            mock.patch.object(
                portfolio_repository_module.PortfolioRepository,
                "get_channel_updater",
                return_value=mock.AsyncMock(fetch_portfolio=mock.AsyncMock(return_value={})),
            ),
            mock.patch.object(
                ohlcv_repository_module.OhlcvRepository,
                "get_channel_updater",
                return_value=mock.AsyncMock(fetch_ohlcv=mock.AsyncMock(return_value=[])),
            ),
            mock.patch.object(
                portfolio_repository_module.trading_api,
                "get_portfolio",
                return_value={},
            ),
            mock.patch.object(
                portfolio_repository_module.personal_data,
                "filter_empty_values",
                side_effect=lambda portfolio: portfolio,
            ),
            mock.patch.object(
                portfolio_repository_module.personal_data,
                "from_raw_to_formatted_portfolio",
                return_value={},
            ),
            mock.patch.object(
                portfolio_repository_module.personal_data,
                "parse_decimal_portfolio",
                return_value={},
            ),
        ):
            trades_repo = trades_repository_module.TradesRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            tickers_repo = tickers_repository_module.TickersRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            orders_repo = orders_repository_module.OrdersRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            portfolio_repo = portfolio_repository_module.PortfolioRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            ohlcv_repo = ohlcv_repository_module.OhlcvRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            exchange_manager.exchange_personal_data = mock.Mock()
            exchange_manager.exchange_personal_data.handle_portfolio_update = mock.AsyncMock(return_value=True)

            await trades_repo.fetch_trades(["BTC/USDT"])
            await tickers_repo.fetch_tickers(["BTC/USDT"])
            await orders_repo.fetch_open_orders(["BTC/USDT"])
            await portfolio_repo.fetch_portfolio()
            await ohlcv_repo.fetch_ohlcv("BTC/USDT", "1h", 10, {})

        create_exchange_channels_mock.assert_not_called()


class TestFetchWiringDagShapedManager:
    async def test_fetch_trades_registers_producer_when_channels_exist_without_one(self):
        exchange_manager = mock.Mock()
        exchange_manager.id = "exchange-manager-2"
        trades_updater = mock.AsyncMock(fetch_trades=mock.AsyncMock(return_value=[]))
        with (
            mock.patch.object(
                trades_repository_module.channel_producer_ensure_module,
                "exchange_has_registered_channels",
                return_value=True,
            ),
            mock.patch.object(
                trades_repository_module.channel_producer_ensure_module,
                "channel_has_producer",
                side_effect=[False, True],
            ),
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ) as create_producers_mock,
            mock.patch.object(
                trades_repository_module.TradesRepository,
                "_get_trades_updater",
                return_value=trades_updater,
            ),
        ):
            trades_repo = trades_repository_module.TradesRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            await trades_repo.fetch_trades(["BTC/USDT"])

        create_producers_mock.assert_awaited_once()
        trades_updater.fetch_trades.assert_awaited_once_with(["BTC/USDT"])


class TestFetchWiringGlobalViewShapedManager:
    async def test_portfolio_and_orders_fetch_create_channels_on_cold_manager(self):
        exchange_manager = mock.Mock()
        exchange_manager.id = "global-view-cold-exchange"
        channels_registered = {"value": False}

        def exchange_has_registered_channels(_exchange_manager):
            return channels_registered["value"]

        async def register_channels_stub(_exchange_manager):
            channels_registered["value"] = True

        balance_updater = mock.Mock()
        balance_updater.fetch_portfolio = mock.AsyncMock(return_value={"USDT": {"total": 1.0, "free": 1.0}})
        orders_updater = mock.Mock()
        orders_updater.fetch_open_orders = mock.AsyncMock(return_value=[])
        with (
            mock.patch.object(
                portfolio_repository_module.channel_producer_ensure_module,
                "exchange_has_registered_channels",
                side_effect=exchange_has_registered_channels,
            ),
            mock.patch(
                "octobot_trading.exchanges.create_exchange_channels",
                mock.AsyncMock(side_effect=register_channels_stub),
            ) as create_exchange_channels_mock,
            mock.patch(
                "octobot_trading.exchanges.create_producers",
                mock.AsyncMock(),
            ),
            mock.patch.object(
                portfolio_repository_module.PortfolioRepository,
                "get_channel_updater",
                return_value=balance_updater,
            ),
            mock.patch.object(
                orders_repository_module.OrdersRepository,
                "get_channel_updater",
                return_value=orders_updater,
            ),
            mock.patch.object(
                portfolio_repository_module.personal_data,
                "filter_empty_values",
                side_effect=lambda portfolio: portfolio,
            ),
            mock.patch.object(
                portfolio_repository_module.personal_data,
                "parse_decimal_portfolio",
                return_value={},
            ),
            mock.patch.object(
                portfolio_repository_module.trading_api,
                "get_portfolio",
                return_value={},
            ),
        ):
            exchange_manager.exchange_personal_data = mock.Mock()
            exchange_manager.exchange_personal_data.handle_portfolio_update = mock.AsyncMock(return_value=True)
            portfolio_repo = portfolio_repository_module.PortfolioRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            orders_repo = orders_repository_module.OrdersRepository(
                exchange_manager, [], _fetched_exchange_data(),
            )
            await portfolio_repo.fetch_and_apply_portfolio()
            await orders_repo.fetch_open_orders(["BTC/USDT"])

        create_exchange_channels_mock.assert_awaited_once_with(exchange_manager)
        balance_updater.fetch_portfolio.assert_awaited_once()
        orders_updater.fetch_open_orders.assert_awaited_once_with(["BTC/USDT"])
