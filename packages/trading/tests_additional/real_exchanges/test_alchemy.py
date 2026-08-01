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

import mock
import pytest

import octobot_commons
import octobot_commons.enums as common_enums
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import tests_additional.real_exchanges as real_exchanges
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


MCADE_BASE = "0xc48823EC67720a04A9DFD8c7d109b2C3D6622094"
WETH_BASE = "0x4200000000000000000000000000000000000006"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_ETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ETH = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
SYMBOL_HYDREX = f"{MCADE_BASE}/{WETH_BASE}{octobot_commons.NETWORK_SEPARATOR}BASE{octobot_commons.DEX_SEPARATOR}HYDREX"
SYMBOL_BASE_UNI = f"{WETH_BASE}/{USDC_BASE}{octobot_commons.NETWORK_SEPARATOR}BASE{octobot_commons.DEX_SEPARATOR}UNISWAPV3"
SYMBOL_ETH_UNI = f"{WETH_ETH}/{USDC_ETH}{octobot_commons.NETWORK_SEPARATOR}ETH{octobot_commons.DEX_SEPARATOR}UNISWAPV3"


pytestmark = pytest.mark.asyncio


def _require_alchemy_api_key():
    real_exchanges._load_exchange_creds_env_variables_if_necessary()
    api_key = os.getenv("ALCHEMY_API_KEY")
    if not api_key:
        pytest.skip("ALCHEMY_API_KEY not set")
    return api_key


def _get_alchemy_additional_connector_config():
    api_key = os.getenv("ALCHEMY_API_KEY")
    if not api_key:
        return {}
    return {
        "apiKey": api_key,
    }


@pytest.fixture(autouse=True)
def require_alchemy_api_key():
    _require_alchemy_api_key()


class TestAlchemyRealExchangeTester(real_exchange_tester.RealExchangeTester):
    """
    Costs 442 Alchemy CU in total to execute 
    """
    EXCHANGE_NAME = "alchemy"
    SYMBOL = SYMBOL_HYDREX
    SYMBOL_2 = SYMBOL_BASE_UNI
    SYMBOL_3 = SYMBOL_ETH_UNI
    USES_TENTACLE = True
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        with mock.patch.object(
            abstract_exchange.AbstractExchange,
            "get_additional_connector_config",
            autospec=True,
            side_effect=lambda self: _get_alchemy_additional_connector_config(),
        ):
            async with super().get_exchange_manager(market_filter=market_filter) as exchange_manager:
                yield exchange_manager

    async def test_time_frames(self):
        time_frames = await self.time_frames()
        assert time_frames is not None

    async def test_supports_order_type(self):
        await self.assert_supports_order_type([])

    async def test_active_symbols(self):
        await self.inner_test_active_symbols(0, 0)

    async def test_get_market_status(self):
        symbols = [self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3]
        await self.assert_lazy_loaded_markets(
            symbols=symbols,
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

    async def test_get_price_ticker(self):
        max_price_per_symbol = {
            self.SYMBOL: 0.01,
            self.SYMBOL_2: 100000,
            self.SYMBOL_3: 100000,
        }
        min_price_per_symbol = {
            self.SYMBOL: 0,
            self.SYMBOL_2: 1000,
            self.SYMBOL_3: 1000,
        }

        def extra_checks(ticker):
            symbol = ticker[real_exchange_tester.Ectc.SYMBOL.value]
            last_price = ticker[real_exchange_tester.Ectc.LAST.value]
            max_price = max_price_per_symbol.get(symbol)
            min_price = min_price_per_symbol.get(symbol)
            if max_price is not None:
                assert last_price < max_price, (
                    f"ticker {symbol} price is too high: {last_price} >= {max_price}"
                )
            if min_price is not None:
                assert last_price > min_price, (
                    f"ticker {symbol} price is too low: {last_price} <= {min_price}"
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

        for symbol in [self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3]:
            await self.assert_get_price_ticker(
                extra_checks=extra_checks,
                symbol=symbol,
                ticker_expectations=_price_ticker_expectations(),
            )

    async def test_get_all_currencies_price_ticker(self):
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

        ticker_expect = real_exchange_tester.TickerExpect
        ticker_expectations = real_exchange_tester.TickerRequiredExpectations(
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

        await self.assert_get_all_currencies_price_ticker(
            symbols=[self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3],
            extra_checks=extra_checks,
            ticker_expectations=ticker_expectations,
        )

    async def test_get_all_currencies_price_ticker_requires_symbols(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_all_currencies_price_ticker()
