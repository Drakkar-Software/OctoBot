#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest
import asyncio

import octobot_trading.exchange_data.ticker.channel.ticker_updater as ticker_updater_module

pytestmark = pytest.mark.asyncio


class TestTickerUpdaterFetchAllTickers:
    async def test_returns_only_requested_symbols_when_exchange_fetches_all_tickers(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "kraken"
        exchange_manager.is_sandboxed = False
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=False)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        updater = ticker_updater_module.TickerUpdater(channel)
        updater.set_cache = mock.Mock()
        all_tickers = {
            "BTC/USDC": {"close": 100000},
            "ETH/USDC": {"close": 3000},
            "INVALID:SYMBOL": {"close": 1},
        }
        updater._fetch_missing_tickers = mock.AsyncMock(return_value=all_tickers)

        with mock.patch.object(
            ticker_updater_module._TICKER_CACHE,
            "get_all_tickers",
            return_value={},
        ):
            tickers = await updater.fetch_all_tickers(["BTC/USDC", "ETH/USDC"])

        assert tickers == {
            "BTC/USDC": {"close": 100000},
            "ETH/USDC": {"close": 3000},
        }
        updater.set_cache.assert_called_once_with("kraken", mock.ANY, False, all_tickers)

    async def test_concurrent_fetch_all_tickers_fetches_missing_symbols_once(self):
        exchange_manager = mock.Mock()
        exchange_manager.exchange_name = "bitmart"
        exchange_manager.is_sandboxed = False
        exchange_manager.exchange.get_option_value = mock.Mock(return_value=True)
        channel = mock.Mock()
        channel.exchange_manager = exchange_manager
        updater = ticker_updater_module.TickerUpdater(channel)
        cached_tickers: dict[str, dict] = {}

        def set_cache_side_effect(exchange_name, exchange_type, sandboxed, tickers):
            cached_tickers.update(tickers)

        updater.set_cache = mock.Mock(side_effect=set_cache_side_effect)
        fetched_tickers = {
            "BTC/USDT": {"close": 100000},
            "ETH/USDT": {"close": 3000},
        }
        fetch_count = 0

        async def fetch_missing_tickers(_missing_symbols):
            nonlocal fetch_count
            fetch_count += 1
            return fetched_tickers

        updater._fetch_missing_tickers = fetch_missing_tickers

        with mock.patch.object(
            ticker_updater_module._TICKER_CACHE,
            "get_all_tickers",
            side_effect=lambda *_args, **_kwargs: cached_tickers,
        ):
            results = await asyncio.gather(
                updater.fetch_all_tickers(["BTC/USDT", "ETH/USDT"]),
                updater.fetch_all_tickers(["BTC/USDT", "ETH/USDT"]),
            )

        assert fetch_count == 1
        assert results[0] == fetched_tickers
        assert results[1] == fetched_tickers
