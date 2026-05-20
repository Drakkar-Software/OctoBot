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
import contextlib

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.enums as common_enums
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


pytestmark = pytest.mark.asyncio


COINGECKO_CCXT_OPTIONS = {
    "vsCurrency": "usd",
}


def _get_coingecko_additional_connector_config():
    # Real-exchange tests only: production should read this from the CoinGecko tentacle
    # via Coingecko.get_additional_connector_config() and tentacle_config.
    return {
        ccxt_constants.CCXT_OPTIONS: COINGECKO_CCXT_OPTIONS,
    }


class TestCoingeckoRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "coingecko"
    SYMBOL = "BTC/USD"
    SYMBOL_2 = "ETH/USD"
    SYMBOL_3 = "SOL/USD"
    USES_TENTACLE = True
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        with mock.patch.object(
            abstract_exchange.AbstractExchange,
            "get_additional_connector_config",
            autospec=True,
            side_effect=lambda self: _get_coingecko_additional_connector_config(),
        ):
            async with super().get_exchange_manager(market_filter=market_filter) as exchange_manager:
                yield exchange_manager

    def get_config(self):
        return {
            commons_constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    commons_constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE,
                    ccxt_constants.CCXT_OPTIONS: COINGECKO_CCXT_OPTIONS,
                }
            }
        }

    async def test_time_frames(self):
        time_frames = await self.time_frames()
        assert time_frames is not None

    async def test_supports_order_type(self):
        await self.assert_supports_order_type([])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(10000, 10000)

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            has_price_limits=False,
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

    def _coingecko_ticker_extra_checks(self, ticker: dict) -> None:
        ticker_columns = trading_enums.ExchangeConstantsTickersColumns
        extra_columns = trading_enums.ExchangeConstantsTickersExtraColumns
        extra = ticker.get(ticker_columns.EXTRA.value)
        assert extra is not None, f"ticker missing {ticker_columns.EXTRA.value!r}"
        assert extra.get(extra_columns.NAME.value), (
            f"ticker extra missing {extra_columns.NAME.value!r}"
        )
        logo_url = extra.get(extra_columns.LOGO_URL.value)
        assert logo_url, f"ticker extra missing {extra_columns.LOGO_URL.value!r}"
        assert isinstance(logo_url, str)
        assert logo_url.startswith("http"), (
            f"ticker {extra_columns.LOGO_URL.value!r} must be an http(s) URL, got {logo_url!r}"
        )

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
            extra_checks=self._coingecko_ticker_extra_checks,
            ticker_expectations=_price_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        symbols = [self.SYMBOL, self.SYMBOL_2]
        await self.assert_get_all_currencies_price_ticker(
            symbols=symbols,
            extra_checks=self._coingecko_ticker_extra_checks,
        )

    async def test_get_all_currencies_price_ticker_without_symbols(self):
        await self.assert_get_all_currencies_price_ticker(
            extra_checks=self._coingecko_ticker_extra_checks,
        )
