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
import os

import pytest
import tentacles  # noqa: F401 — registers Coingecko exchange tentacle for USES_TENTACLE

import octobot_commons
import octobot_commons.enums as common_enums
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import tests_additional.real_exchanges as real_exchanges_test_util
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
UNI_ADDRESS = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"
NETWORK_NAME = "ETH"
NO_DEX_SYMBOL_SUFFIX = f"{octobot_commons.NETWORK_SEPARATOR}{NETWORK_NAME}"
ANY_DEX_SYMBOL_SUFFIX = f"{octobot_commons.NETWORK_SEPARATOR}{NETWORK_NAME}{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"

WETH_BASE_ADDRESS = "0x4200000000000000000000000000000000000006"
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
NETWORK_NAME_2 = "BASE"
ANY_DEX_SYMBOL_SUFFIX_2 = f"{octobot_commons.NETWORK_SEPARATOR}{NETWORK_NAME_2}{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"


pytestmark = pytest.mark.asyncio


def _get_coingecko_api_key():
    real_exchanges_test_util._load_exchange_creds_env_variables_if_necessary()
    return os.getenv("COINGECKO_API_KEY")


def _require_coingecko_onchain_api_key():
    if not _get_coingecko_api_key():
        pytest.skip("COINGECKO_API_KEY environment variable is required for onchain CoinGecko tests")

class TestCoingeckoRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "coingecko"
    SYMBOL = "BTC/USD"
    SYMBOL_2 = "ETH/USD"
    SYMBOL_3 = "SOL/USD"
    ONCHAIN_SYMBOL = f"{WETH_ADDRESS}/{USDC_ADDRESS}{NO_DEX_SYMBOL_SUFFIX}"
    ONCHAIN_SYMBOL_2 = f"{WETH_ADDRESS}/{USDT_ADDRESS}{ANY_DEX_SYMBOL_SUFFIX}"
    ONCHAIN_SYMBOL_3 = f"{UNI_ADDRESS}/{WETH_ADDRESS}{ANY_DEX_SYMBOL_SUFFIX}"
    ONCHAIN_SYMBOL_4 = f"{USDT_ADDRESS}/USD{NO_DEX_SYMBOL_SUFFIX}"
    ONCHAIN_SYMBOL_5 = f"{WETH_BASE_ADDRESS}/{USDC_BASE_ADDRESS}{ANY_DEX_SYMBOL_SUFFIX_2}"
    USES_TENTACLE = True
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        real_exchanges_test_util._load_exchange_creds_env_variables_if_necessary()
        async with super().get_exchange_manager(market_filter=market_filter) as exchange_manager:
            yield exchange_manager

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

    def _coingecko_ticker_expectations(self) -> real_exchange_tester.TickerRequiredExpectations:
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
            timestamp=ticker_expect.TRUTHY,
        )

    async def test_get_price_ticker(self):
        await self.assert_get_price_ticker(
            extra_checks=self._coingecko_ticker_extra_checks,
            ticker_expectations=self._coingecko_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker(self):
        symbols = [self.SYMBOL, self.SYMBOL_2]
        await self.assert_get_all_currencies_price_ticker(
            symbols=symbols,
            extra_checks=self._coingecko_ticker_extra_checks,
            ticker_expectations=self._coingecko_ticker_expectations(),
        )

    async def test_get_all_currencies_price_ticker_without_symbols(self):
        await self.assert_get_all_currencies_price_ticker(
            extra_checks=self._coingecko_ticker_extra_checks,
            ticker_expectations=self._coingecko_ticker_expectations(),
        )

    async def test_get_market_status_onchain_symbols(self):
        _require_coingecko_onchain_api_key()
        symbols = [
            self.ONCHAIN_SYMBOL,
            self.ONCHAIN_SYMBOL_2,
            self.ONCHAIN_SYMBOL_3,
            self.ONCHAIN_SYMBOL_4,
            self.ONCHAIN_SYMBOL_5,
        ]
        await self.assert_lazy_loaded_markets(
            symbols=symbols,
            has_price_limits=False,
            can_have_cache=True,
        )

    async def test_get_price_ticker_onchain_symbols(self):
        _require_coingecko_onchain_api_key()
        max_price_per_symbol = {
            self.ONCHAIN_SYMBOL: 99999,
            self.ONCHAIN_SYMBOL_2: 99999,
            self.ONCHAIN_SYMBOL_3: 1,
            self.ONCHAIN_SYMBOL_4: 2,
            self.ONCHAIN_SYMBOL_5: 99999,
        }

        def extra_checks(ticker):
            symbol = ticker[real_exchange_tester.Ectc.SYMBOL.value]
            max_price = max_price_per_symbol.get(symbol)
            if max_price:
                assert ticker[real_exchange_tester.Ectc.LAST.value] < max_price, (
                    f"ticker {symbol} price is too high: "
                    f"{ticker[real_exchange_tester.Ectc.LAST.value]} > {max_price}"
                )
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_open=False,
                check_high=False,
                check_low=False,
                check_base_volume=False,
                check_quote_volume=False,
                check_last=True,
            )
            self._coingecko_ticker_extra_checks(ticker)

        for symbol in [
            self.ONCHAIN_SYMBOL,
            self.ONCHAIN_SYMBOL_2,
            self.ONCHAIN_SYMBOL_3,
            self.ONCHAIN_SYMBOL_4,
        ]:
            await self.assert_get_price_ticker(
                extra_checks=extra_checks,
                symbol=symbol,
                ticker_expectations=self._coingecko_ticker_expectations(),
            )

    async def test_get_all_currencies_price_ticker_onchain_symbols(self):
        _require_coingecko_onchain_api_key()
        def extra_checks(ticker):
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_open=False,
                check_high=False,
                check_low=False,
                check_base_volume=False,
                check_quote_volume=False,
                check_last=True,
            )
            self._coingecko_ticker_extra_checks(ticker)

        await self.assert_get_all_currencies_price_ticker(
            symbols=[
                self.ONCHAIN_SYMBOL,
                self.ONCHAIN_SYMBOL_2,
                self.ONCHAIN_SYMBOL_3,
                self.ONCHAIN_SYMBOL_4,
                self.ONCHAIN_SYMBOL_5,
            ],
            extra_checks=extra_checks,
            ticker_expectations=self._coingecko_ticker_expectations(),
        )
