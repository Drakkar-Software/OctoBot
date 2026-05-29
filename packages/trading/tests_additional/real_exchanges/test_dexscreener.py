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

import octobot_commons
import octobot_commons.constants as commons_constants
import octobot_commons.enums as common_enums
import octobot_trading.errors as trading_errors
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import tests_additional.real_exchanges.real_exchange_tester as real_exchange_tester


WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
UNI_ADDRESS = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"
LINK_ADDRESS = "0x514910771AF9Ca656af840dff83E8264EcF986CA"
NETWORK_NAME = "ETH"
DEX_NAME = "UNISWAP"
SYMBOL_SUFFIX = f"{octobot_commons.NETWORK_SEPARATOR}{NETWORK_NAME}{octobot_commons.DEX_SEPARATOR}{DEX_NAME}"
ANY_DEX_SYMBOL_SUFFIX = f"{octobot_commons.NETWORK_SEPARATOR}{NETWORK_NAME}{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"


pytestmark = pytest.mark.asyncio


class TestDexScreenerRealExchangeTester(real_exchange_tester.RealExchangeTester):
    EXCHANGE_NAME = "dexscreener"
    SYMBOL = f"{WETH_ADDRESS}/{USDC_ADDRESS}{SYMBOL_SUFFIX}"
    SYMBOL_2 = f"{WETH_ADDRESS}/{USDT_ADDRESS}{SYMBOL_SUFFIX}"
    SYMBOL_3 = f"{WETH_ADDRESS}/{USDT_ADDRESS}{ANY_DEX_SYMBOL_SUFFIX}"
    # SYMBOL_3 = f"WETH/USDT{SYMBOL_SUFFIX}"
    SYMBOL_4 = f"{UNI_ADDRESS}/{USDC_ADDRESS}{SYMBOL_SUFFIX}"
    SYMBOL_5 = f"{UNI_ADDRESS}/{WETH_ADDRESS}{SYMBOL_SUFFIX}"
    SYMBOL_6 = f"{WETH_ADDRESS}/{USDT_ADDRESS}{SYMBOL_SUFFIX}"
    USES_TENTACLE = False
    TIME_FRAME = common_enums.TimeFrames.ONE_DAY
    REQUIRES_AUTH = False

    async def test_time_frames(self):
        # DexScreener does not support OHLCV / time frames.
        time_frames = await self.time_frames()
        # Expect at least the default time frame to be listed even if OHLCV is unsupported.
        assert time_frames is not None

    async def test_supports_order_type(self):
        await self.assert_supports_order_type([])

    async def test_active_symbols(self):
        # no active symbols by default
        await self.inner_test_active_symbols(0, 0)

    async def test_get_dex_pairs(self):
        Ecdpc = trading_enums.ExchangeConstantsDexPairsColumns

        await self.assert_get_dex_pairs(
            symbols=[self.SYMBOL, self.SYMBOL_2],
            expected_network=NETWORK_NAME,
            expected_dex=DEX_NAME,
            expected_ticker_symbols={"WETH/USDC", "WETH/USDT"},
            min_result_count=2,
            max_price_per_symbol={"WETH/USDC": 99999, "WETH/USDT": 99999},
        )
        def _check_multiple_eth_dexes_for_wildcard(dex_pairs: list[dict]) -> None:
            dexes = {dex_pair[Ecdpc.DEX.value] for dex_pair in dex_pairs}
            assert len(dexes) >= 2, (
                f"expected multiple concrete dexes for {self.SYMBOL_3!r}, got {dexes!r}"
            )

        await self.assert_get_dex_pairs(
            symbols=[self.SYMBOL_3],
            expected_network=NETWORK_NAME,
            expected_ticker_symbols={"WETH/USDT"},
            min_result_count=2,
            max_price_per_symbol={"WETH/USDT": 99999},
            extra_checks=_check_multiple_eth_dexes_for_wildcard,
        )
        plain_weth_usdc = f"{WETH_ADDRESS}/{USDC_ADDRESS}"
        plain_uni_usdc = f"{UNI_ADDRESS}/{USDC_ADDRESS}"
        required_ticker_symbols = {"WETH/USDC", "UNI/USDC"}

        def _check_multiple_venues_for_required_pairs(dex_pairs: list[dict]) -> None:
            venues: dict[tuple[str, str], set[str]] = {}
            for dex_pair in dex_pairs:
                venue_key = (dex_pair[Ecdpc.NETWORK.value], dex_pair[Ecdpc.DEX.value])
                venues.setdefault(venue_key, set()).add(dex_pair[Ecdpc.SYMBOL.value])
            assert len(venues) >= 1, (
                f"expected at least one network/dex venue for plain address pairs, got {list(venues)}"
            )
            for venue_key, ticker_symbols in venues.items():
                assert ticker_symbols == required_ticker_symbols, (
                    f"venue {venue_key} must list every required pair only, got {ticker_symbols}"
                )
            assert len(dex_pairs) == len(venues) * len(required_ticker_symbols), (
                f"each venue must expose all required pairs exactly once: "
                f"{len(dex_pairs)} results for {len(venues)} venues"
            )

        await self.assert_get_dex_pairs(
            symbols=[plain_weth_usdc, plain_uni_usdc],
            expected_ticker_symbols=required_ticker_symbols,
            min_result_count=2,
            max_price_per_symbol={"WETH/USDC": 99999, "UNI/USDC": 99999},
            extra_checks=_check_multiple_venues_for_required_pairs,
        )

        plain_link_weth = f"{LINK_ADDRESS}/{WETH_ADDRESS}"
        link_weth_required_ticker_symbols = {"LINK/WETH", "WETH/USDC"}

        def _check_multiple_venues_for_link_weth_pairs(dex_pairs: list[dict]) -> None:
            venues: dict[tuple[str, str], set[str]] = {}
            pair_venues: dict[str, set[tuple[str, str]]] = {}
            for dex_pair in dex_pairs:
                venue_key = (dex_pair[Ecdpc.NETWORK.value], dex_pair[Ecdpc.DEX.value])
                ticker_symbol = dex_pair[Ecdpc.SYMBOL.value]
                venues.setdefault(venue_key, set()).add(ticker_symbol)
                pair_venues.setdefault(ticker_symbol, set()).add(venue_key)
            assert len(venues) >= 2, (
                f"expected multiple network/dex venues for plain LINK/WETH address pairs, got {list(venues)}"
            )
            for ticker_symbol in link_weth_required_ticker_symbols:
                assert len(pair_venues.get(ticker_symbol, set())) > 1, (
                    f"expected {ticker_symbol} on multiple venues, got {pair_venues.get(ticker_symbol, set())}"
                )
            for venue_key, ticker_symbols in venues.items():
                assert ticker_symbols == link_weth_required_ticker_symbols, (
                    f"venue {venue_key} must list every required pair only, got {ticker_symbols}"
                )
            assert len(dex_pairs) == len(venues) * len(link_weth_required_ticker_symbols), (
                f"each venue must expose all required pairs exactly once: "
                f"{len(dex_pairs)} results for {len(venues)} venues"
            )

        await self.assert_get_dex_pairs(
            symbols=[plain_link_weth, plain_weth_usdc],
            expected_ticker_symbols=link_weth_required_ticker_symbols,
            min_result_count=4,
            max_price_per_symbol={"LINK/WETH": 1, "WETH/USDC": 99999},
            extra_checks=_check_multiple_venues_for_link_weth_pairs,
        )

    async def test_get_market_status(self):
        symbols = [
            self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3, self.SYMBOL_4, self.SYMBOL_5,
            "WETH/USDC", "UNI/USDC", "WETH/USDT"
        ]
        await self.assert_lazy_loaded_markets(
            symbols=symbols,
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
            symbols=[self.SYMBOL, self.SYMBOL_2, self.SYMBOL_3, self.SYMBOL_4, self.SYMBOL_5],
            extra_checks=extra_checks,
        )

    async def test_get_all_currencies_price_ticker_requires_symbols(self):
        with pytest.raises(trading_errors.NotSupported):
            await self.get_all_currencies_price_ticker()
