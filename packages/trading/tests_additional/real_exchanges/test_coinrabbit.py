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
import pytest

import octobot_commons.enums as common_enums
import octobot_commons.symbols as commons_symbols
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


pytestmark = pytest.mark.asyncio


class TestCoinrabbitRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "coinrabbit"
    SYMBOL = "BTC@BTC/USDT@ETH"
    SYMBOL_2 = "BTC@BTC/USDT@BSC"
    SYMBOL_3 = "BTC@BTC/USDT@ARBITRUM"
    USES_TENTACLE = False
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    async def test_time_frames(self):
        time_frames = await self.time_frames()
        assert time_frames is not None

    async def test_supports_order_type(self):
        await self.assert_supports_order_type([trading_enums.TradeOrderType.MARKET])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(8, 8)

    async def test_ticker_wise_symbol_parsing(self):
        symbol = commons_symbols.parse_symbol(self.SYMBOL)
        assert symbol.has_ticker_wise_networks() is True
        assert symbol.base == "BTC"
        assert symbol.base_network == "BTC"
        assert symbol.quote == "USDT"
        assert symbol.quote_network == "ETH"

    async def test_get_market_status(self):
        def extra_checks(market_status: dict) -> None:
            connector_market = market_status.get(real_exchange_tester.Ecmsc.INFO.value, {})
            assert connector_market.get("base_network"), "market info must preserve base_network"
            assert connector_market.get("quote_network"), "market info must preserve quote_network"

        await self.assert_get_market_status(
            has_price_limits=False,
            extra_checks=extra_checks,
        )

    async def test_get_symbol_prices(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_symbol_prices()

    async def test_get_historical_symbol_prices(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_symbol_prices(limit=1000)

    async def test_get_historical_ohlcv(self):
        with pytest.raises(trading_errors.NotSupported):
            await super().test_get_historical_ohlcv()

    async def test_get_kline_price(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_kline_price()

    async def test_get_order_book(self):
        with pytest.raises(trading_errors.NotSupported):
            async with self.get_exchange_manager() as exchange_manager:
                await exchange_manager.exchange.get_order_book(self.SYMBOL)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_recent_trades()

    async def test_get_price_ticker(self):
        def _price_ticker_expectations() -> real_exchange_tester.TickerRequiredExpectations:
            ticker_expect = real_exchange_tester.TickerExpect
            return real_exchange_tester.TickerRequiredExpectations(
                open=ticker_expect.NONE,
                high=ticker_expect.NONE,
                low=ticker_expect.NONE,
                close=ticker_expect.TRUTHY,
                last=ticker_expect.TRUTHY,
                bid_volume=ticker_expect.NONE,
                ask_volume=ticker_expect.NONE,
                base_volume=ticker_expect.NONE,
                quote_volume=ticker_expect.NONE,
                previous_close=ticker_expect.NONE,
            )

        await self.assert_get_price_ticker(
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        with pytest.raises(trading_errors.NotSupported):
            async with self.get_exchange_manager() as exchange_manager:
                await exchange_manager.exchange.get_all_currencies_price_ticker(
                    symbols=[self.SYMBOL, self.SYMBOL_2],
                )
