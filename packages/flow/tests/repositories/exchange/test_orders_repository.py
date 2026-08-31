#  Drakkar-Software OctoBot-Flow

import mock
import pytest

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data

import octobot_flow.entities
import octobot_flow.repositories.exchange.orders_repository as orders_repository_module

pytestmark = pytest.mark.asyncio


def _open_order_dict(exchange_id: str, symbol: str) -> dict:
    return {
        trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,
        trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,
        trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0,
    }


class TestFetchOpenOrders:
    async def test_returns_parsed_orders_from_updater(self):
        eth_order = _open_order_dict("stays-order-2", "ETH/USDT")
        parsed_order = {
            trading_constants.STORAGE_ORIGIN_VALUE: eth_order,
        }
        exchange_manager = mock.Mock()
        orders_updater = mock.Mock()
        orders_updater.fetch_open_orders = mock.AsyncMock(return_value=[eth_order])
        repository = orders_repository_module.OrdersRepository(
            exchange_manager,
            known_automations=[],
            fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
        )
        with (
            mock.patch.object(
                repository,
                "get_channel_updater",
                return_value=orders_updater,
            ),
            mock.patch.object(
                trading_personal_data.OrdersUpdater,
                "ensure_parsing",
                return_value=parsed_order,
            ) as ensure_parsing_mock,
        ):
            open_orders = await repository.fetch_open_orders(["STRK/USDC", "ETH/USDT"])

        orders_updater.fetch_open_orders.assert_awaited_once_with(["STRK/USDC", "ETH/USDT"])
        ensure_parsing_mock.assert_called_once_with(
            exchange_manager,
            eth_order,
            True,
            True,
        )
        assert open_orders == [parsed_order]

    async def test_returns_empty_list_when_no_symbols(self):
        exchange_manager = mock.Mock()
        repository = orders_repository_module.OrdersRepository(
            exchange_manager,
            known_automations=[],
            fetched_exchange_data=octobot_flow.entities.FetchedExchangeData(),
        )
        open_orders = await repository.fetch_open_orders([])
        assert open_orders == []
