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
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
UNI_ADDRESS = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"

DEXSCREENER_CCXT_OPTIONS = {
    "chainId": "ethereum",
    "dexId": "uniswap",
    "baseTokenAddresses": [
        WETH_ADDRESS,
        UNI_ADDRESS,
    ],
    "quoteTokenAddresses": [
        WETH_ADDRESS,
        USDC_ADDRESS,
        USDT_ADDRESS,
    ],
}


def _get_dexscreener_additional_connector_config():
    # Real-exchange tests only: production should read these from the DexScreener tentacle
    # via DexScreener.get_additional_connector_config() and tentacle_config.
    return {
        ccxt_constants.CCXT_OPTIONS: DEXSCREENER_CCXT_OPTIONS,
    }


pytestmark = pytest.mark.asyncio


class TestDexScreenerRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "dexscreener"
    SYMBOL = "WETH/USDC"
    SYMBOL_2 = "WETH/USDT"
    SYMBOL_3 = f"{WETH_ADDRESS.lower()}/{USDT_ADDRESS.lower()}"
    SYMBOL_4 = "UNI/USDC"
    SYMBOL_5 = "UNI/WETH"
    USES_TENTACLE = False
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    @contextlib.asynccontextmanager
    async def get_exchange_manager(self, market_filter=None):
        with mock.patch.object(
            abstract_exchange.AbstractExchange,
            "get_additional_connector_config",
            autospec=True,
            side_effect=lambda self: _get_dexscreener_additional_connector_config(),
        ):
            async with super().get_exchange_manager(market_filter=market_filter) as exchange_manager:
                yield exchange_manager

    def get_config(self):
        return {
            commons_constants.CONFIG_EXCHANGES: {
                self.EXCHANGE_NAME: {
                    commons_constants.CONFIG_EXCHANGE_TYPE: self.EXCHANGE_TYPE,
                    ccxt_constants.CCXT_OPTIONS: DEXSCREENER_CCXT_OPTIONS,
                }
            }
        }

    async def test_time_frames(self):
        # DexScreener does not support OHLCV / time frames.
        time_frames = await self.time_frames()
        # Expect at least the default time frame to be listed even if OHLCV is unsupported.
        assert time_frames is not None

    async def test_supports_order_type(self):
        await self.assert_supports_order_type([])

    async def test_active_symbols(self):
        # WETH/USDC, WETH/USDT, UNI/USDC, UNI/USDT, and address-pair aliases for each
        await self.inner_test_active_symbols(8, 8)

    async def test_get_exchange_symbol(self):
        await self.assert_get_exchange_symbol({
            self.SYMBOL: (self.SYMBOL, "WETH", "USDC"),
            self.SYMBOL_2: (self.SYMBOL_2, "WETH", "USDT"),
            self.SYMBOL_3: (self.SYMBOL_2, "WETH", "USDT"),
            self.SYMBOL_4: (self.SYMBOL_4, "UNI", "USDC"),
            self.SYMBOL_5: (self.SYMBOL_5, "UNI", "WETH"),
            f"{WETH_ADDRESS}/{USDT_ADDRESS}": (self.SYMBOL_2, "WETH", "USDT"),
        })

    async def test_get_market_status(self):
        await self.assert_get_market_status(
            has_price_limits=False,
        )

    async def test_get_symbol_prices(self):
        # DexScreener does not support OHLCV / klines.
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
        # DexScreener does not have an order book — it is a data provider.
        with pytest.raises(trading_errors.NotSupported):
            async with self.get_exchange_manager() as exchange_manager:
                await exchange_manager.exchange.get_order_book(self.SYMBOL)

    async def test_get_order_books(self):
        await self.inner_test_unsupported_get_order_books()

    async def test_get_recent_trades(self):
        # DexScreener does not expose trade history.
        with pytest.raises(trading_errors.NotSupported):
            await self.get_recent_trades()

    async def test_get_price_ticker(self):
        max_price_per_symbol = {
            # WETH/USDT and WETH/USDC should be valued at less than 100,000 USD
            self.SYMBOL: 99999,
            self.SYMBOL_3: 99999,
            # UNI/WETH should be valued at less than 1 WETH
            self.SYMBOL_5: 1,
        }
        def extra_checks(ticker):
            symbol = ticker[real_exchange_tester.Ectc.SYMBOL.value]
            max_price = max_price_per_symbol.get(symbol, None)
            if max_price:
                assert ticker[real_exchange_tester.Ectc.LAST.value] < max_price, (
                    f"ticker {symbol} price is too high: {ticker[real_exchange_tester.Ectc.LAST.value]} > {max_price}"
                )
            real_exchange_tester.RealExchangeTester.check_ticker_typing(
                ticker,
                check_open=False,
                check_high=False,
                check_low=False,
                check_base_volume=False,
                check_quote_volume=True,
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
                quote_volume=ticker_expect.TRUTHY,
                previous_close=ticker_expect.NONE,
            )
        # ensure both regular symbols and address-pair symbols are supported
        for symbol in [self.SYMBOL, self.SYMBOL_3, self.SYMBOL_5]:
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
                check_quote_volume=True,
                check_last=True,
            )
            ticker_expect = real_exchange_tester.TickerExpect
            real_exchange_tester.RealExchangeTester._check_ticker_required_content(
                ticker,
                ticker_expectations=real_exchange_tester.TickerRequiredExpectations(
                    open=ticker_expect.NONE,
                    high=ticker_expect.NONE,
                    low=ticker_expect.NONE,
                    close=ticker_expect.TRUTHY,
                    last=ticker_expect.TRUTHY,
                    bid_volume=ticker_expect.NONE,
                    ask_volume=ticker_expect.NONE,
                    base_volume=ticker_expect.NONE,
                    quote_volume=ticker_expect.TRUTHY,
                    previous_close=ticker_expect.NONE,
                ),
            )

        await self.assert_get_all_currencies_price_ticker(
            symbols=[self.SYMBOL, self.SYMBOL_2, self.SYMBOL_4, self.SYMBOL_5],
            extra_checks=extra_checks,
        )

    async def test_get_all_currencies_price_ticker_requires_symbols(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_all_currencies_price_ticker()
