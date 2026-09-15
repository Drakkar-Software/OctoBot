import mock
import pytest

import octobot_trading.enums as enums
import octobot_trading.exchanges.types.rest_exchange as rest_exchange_module


class TestRestExchangeGetMyRecentTradesExhaustHistory:
    @pytest.mark.asyncio
    async def test_routes_closed_orders_when_require_recent_trades_from_closed_orders(self):
        exchange = mock.MagicMock()
        exchange.get_closed_orders = mock.AsyncMock(return_value=[{"id": "order-1"}])
        exchange.connector = mock.MagicMock()
        exchange.connector.get_my_recent_trades = mock.AsyncMock()

        def get_option_value(option_key):
            if option_key == enums.ExchangeClientOptions.REQUIRE_RECENT_TRADES_FROM_CLOSED_ORDERS:
                return True
            return enums.DEFAULT_EXCHANGE_OPTION_VALUES.get(option_key)

        exchange.get_option_value = get_option_value

        result = await rest_exchange_module.RestExchange.get_my_recent_trades(
            exchange,
            symbol="SOL/USDT",
            exhaust_history=True,
        )

        exchange.get_closed_orders.assert_awaited_once_with(
            symbol="SOL/USDT",
            since=None,
            limit=None,
            exhaust_history=True,
        )
        exchange.connector.get_my_recent_trades.assert_not_awaited()
        assert result == [{"id": "order-1"}]


class TestRestExchangeGetExchangeAvailabilities:
    def test_default_returns_empty_list(self):
        assert rest_exchange_module.RestExchange.get_exchange_availabilities() == []
