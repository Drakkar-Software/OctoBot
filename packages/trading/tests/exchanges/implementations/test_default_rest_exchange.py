# pylint: disable=E0611
#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_commons.enums as commons_enums
import mock
import octobot_trading.constants as constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as errors
import octobot_trading.exchanges as exchanges
import pytest

from tests.exchanges import exchange_manager, DEFAULT_EXCHANGE_NAME, MockedRestExchange

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def default_rest_exchange(exchange_manager):
    return MockedRestExchange(exchange_manager.config, exchange_manager, None)


async def test_start_request_data_and_stop(default_rest_exchange):
    await default_rest_exchange.initialize()
    symbol = "BTC/USDT"
    try:
        assert len(default_rest_exchange.symbols) > 10
        assert len(default_rest_exchange.time_frames) > 5
        market_status = default_rest_exchange.get_market_status(symbol)
        assert isinstance(market_status, dict)
        assert market_status
        ohlcv = await default_rest_exchange.get_symbol_prices(symbol, commons_enums.TimeFrames.ONE_HOUR)
        assert isinstance(ohlcv, list)
        assert len(ohlcv) > 50
        trades = await default_rest_exchange.get_recent_trades(symbol)
        assert isinstance(trades, list)
        assert len(trades) > 5
        ticker = await default_rest_exchange.get_price_ticker(symbol)
        assert isinstance(ticker, dict)
        assert ticker
        book = await default_rest_exchange.get_order_book(symbol)
        assert isinstance(book, dict)
        assert book
    finally:
        await default_rest_exchange.stop()


class TestDefaultRestExchangeEnsureApiKeyPermissions:

    async def test_ignored_when_permissions_fetch_is_not_supported(self, default_rest_exchange):
        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(side_effect=errors.NotSupported()),
        ) as get_permissions_mock:
            assert await default_rest_exchange.ensure_api_key_permissions(test_param=True) is None

        get_permissions_mock.assert_awaited_once_with(test_param=True)

    async def test_accepts_spot_permissions_without_withdrawals(self, default_rest_exchange):
        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[
                trading_enums.APIKeyRights.READING,
                trading_enums.APIKeyRights.SPOT_TRADING,
            ]),
        ):
            assert await default_rest_exchange.ensure_api_key_permissions() is None

    async def test_accepts_futures_permissions_without_withdrawals(self, default_rest_exchange):
        default_rest_exchange.exchange_manager.is_spot_only = False
        default_rest_exchange.exchange_manager.is_future = True

        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[
                trading_enums.APIKeyRights.READING,
                trading_enums.APIKeyRights.FUTURES_TRADING,
            ]),
        ):
            assert await default_rest_exchange.ensure_api_key_permissions() is None

    async def test_rejects_empty_permissions(self, default_rest_exchange):
        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[]),
        ):
            with pytest.raises(errors.InvalidAPIKeyPermissionsError, match="No permissions found"):
                await default_rest_exchange.ensure_api_key_permissions()

    async def test_rejects_permissions_without_reading(self, default_rest_exchange):
        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[trading_enums.APIKeyRights.SPOT_TRADING]),
        ):
            with pytest.raises(errors.InvalidAPIKeyPermissionsError, match="READING permission is required"):
                await default_rest_exchange.ensure_api_key_permissions()

    async def test_rejects_spot_only_exchange_without_spot_trading(self, default_rest_exchange):
        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[trading_enums.APIKeyRights.READING]),
        ):
            with pytest.raises(errors.InvalidAPIKeyPermissionsError, match="SPOT_TRADING permission is required"):
                await default_rest_exchange.ensure_api_key_permissions()

    async def test_rejects_future_exchange_without_futures_trading(self, default_rest_exchange):
        default_rest_exchange.exchange_manager.is_spot_only = False
        default_rest_exchange.exchange_manager.is_future = True

        with mock.patch.object(
            default_rest_exchange,
            "get_permissions",
            mock.AsyncMock(return_value=[trading_enums.APIKeyRights.READING]),
        ):
            with pytest.raises(errors.InvalidAPIKeyPermissionsError, match="FUTURES_TRADING permission is required"):
                await default_rest_exchange.ensure_api_key_permissions()

    async def test_rejects_withdrawals_when_funds_transfer_is_disabled(self, default_rest_exchange):
        with (
            mock.patch.object(constants, "ALLOW_FUNDS_TRANSFER", False),
            mock.patch.object(
                default_rest_exchange,
                "get_permissions",
                mock.AsyncMock(return_value=[
                    trading_enums.APIKeyRights.READING,
                    trading_enums.APIKeyRights.SPOT_TRADING,
                    trading_enums.APIKeyRights.WITHDRAWALS,
                ]),
            ),
        ):
            with pytest.raises(errors.InvalidAPIKeyPermissionsError, match="WITHDRAWALS permission found"):
                await default_rest_exchange.ensure_api_key_permissions()

    async def test_accepts_withdrawals_when_funds_transfer_is_enabled(self, default_rest_exchange):
        with (
            mock.patch.object(constants, "ALLOW_FUNDS_TRANSFER", True),
            mock.patch.object(
                default_rest_exchange,
                "get_permissions",
                mock.AsyncMock(return_value=[
                    trading_enums.APIKeyRights.READING,
                    trading_enums.APIKeyRights.SPOT_TRADING,
                    trading_enums.APIKeyRights.WITHDRAWALS,
                ]),
            ),
        ):
            assert await default_rest_exchange.ensure_api_key_permissions() is None


class TestDefaultRestExchangeLazyMarketLoading:

    async def test_ensure_lazy_market_loaded_calls_load_markets_for_symbols(self, default_rest_exchange):
        symbol = "BTC/ETH"
        default_rest_exchange.connector.client.markets = {}
        with (
            mock.patch.object(default_rest_exchange, "lazy_load_markets", mock.Mock(return_value=True)),
            mock.patch.object(
                default_rest_exchange,
                "load_markets_for_symbols",
                mock.AsyncMock(return_value=[{"symbol": symbol}]),
            ) as load_markets_for_symbols_mock,
        ):
            await default_rest_exchange.ensure_lazy_market_loaded(symbol)

        load_markets_for_symbols_mock.assert_awaited_once_with([symbol])

    async def test_ensure_lazy_market_loaded_skips_when_symbol_already_loaded(self, default_rest_exchange):
        symbol = "BTC/ETH"
        default_rest_exchange.connector.client.markets = {symbol: {"symbol": symbol}}
        with (
            mock.patch.object(default_rest_exchange, "lazy_load_markets", mock.Mock(return_value=True)),
            mock.patch.object(
                default_rest_exchange,
                "load_markets_for_symbols",
                mock.AsyncMock(),
            ) as load_markets_for_symbols_mock,
        ):
            await default_rest_exchange.ensure_lazy_market_loaded(symbol)

        load_markets_for_symbols_mock.assert_not_awaited()

    async def test_ensure_lazy_market_loaded_noop_when_lazy_load_disabled(self, default_rest_exchange):
        symbol = "BTC/ETH"
        default_rest_exchange.connector.client.markets = {}
        with (
            mock.patch.object(default_rest_exchange, "lazy_load_markets", mock.Mock(return_value=False)),
            mock.patch.object(
                default_rest_exchange,
                "load_markets_for_symbols",
                mock.AsyncMock(),
            ) as load_markets_for_symbols_mock,
        ):
            await default_rest_exchange.ensure_lazy_market_loaded(symbol)

        load_markets_for_symbols_mock.assert_not_awaited()

    async def test_get_market_status_including_lazy_load_ensures_before_get_market_status(self, default_rest_exchange):
        symbol = "BTC/ETH"
        market_status = {"symbol": symbol, "limits": {}}
        with (
            mock.patch.object(
                default_rest_exchange,
                "ensure_lazy_market_loaded",
                mock.AsyncMock(),
            ) as ensure_lazy_market_loaded_mock,
            mock.patch.object(
                default_rest_exchange,
                "get_market_status",
                mock.Mock(return_value=market_status),
            ) as get_market_status_mock,
        ):
            result = await default_rest_exchange.get_market_status_including_lazy_load(symbol, with_fixer=False)

        ensure_lazy_market_loaded_mock.assert_awaited_once_with(symbol)
        get_market_status_mock.assert_called_once_with(symbol, price_example=None, with_fixer=False)
        assert result is market_status
