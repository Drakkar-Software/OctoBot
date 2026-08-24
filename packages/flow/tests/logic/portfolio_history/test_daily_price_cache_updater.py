import time
import mock
import pytest

import octobot_trading.api as trading_api
import octobot_trading.errors as trading_errors

import octobot_commons.constants as commons_constants
import octobot_flow.constants as flow_constants
import octobot_flow.logic.portfolio_history.daily_price_cache_updater as daily_price_cache_updater_module


def _exchange_manager_with_symbols(symbols: list[str], exchange_name: str = "binance"):
    exchange_manager = mock.AsyncMock()
    exchange_manager.client_symbols = symbols
    exchange_manager.exchange_name = exchange_name
    return exchange_manager


async def _empty_historical_ohlcv(*_args, **_kwargs):
    if False:
        yield []


def _patch_historical_ohlcv(candles=None, error=None):
    async def _historical_ohlcv(*_args, **_kwargs):
        if error is not None:
            raise error
        if candles:
            yield candles

    return mock.patch.object(
        daily_price_cache_updater_module.exchange_util,
        "get_historical_ohlcv",
        _historical_ohlcv,
    )


@pytest.fixture(autouse=True)
def mock_empty_historical_ohlcv():
    with mock.patch.object(
        daily_price_cache_updater_module.exchange_util,
        "get_historical_ohlcv",
        _empty_historical_ohlcv,
    ):
        yield


class TestComputeFetchTimeRangeMs:
    def test_incremental_uses_since_ms_as_start(self):
        since_ms = 1_700_000_000_000
        start_time_ms, end_time_ms = daily_price_cache_updater_module._compute_fetch_time_range_ms(since_ms)
        assert start_time_ms == since_ms
        assert end_time_ms > since_ms

    def test_empty_cache_uses_lookback_start(self):
        start_time_ms, end_time_ms = daily_price_cache_updater_module._compute_fetch_time_range_ms(None)
        lookback_ms = (
            flow_constants.PORTFOLIO_HISTORY_DAILY_LOOKBACK_DAYS
            * commons_constants.DAYS_TO_SECONDS
            * commons_constants.MSECONDS_TO_SECONDS
        )
        assert end_time_ms - start_time_ms == lookback_ms


class TestComputeFetchSinceMs:
    def test_empty_cache_returns_none(self):
        daily_prices = {"symbols": {}, "sources": {}}
        assert daily_price_cache_updater_module._compute_fetch_since_ms(
            daily_prices, "BTC/USDT",
        ) is None

    def test_uses_newest_minus_one_day(self):
        daily_prices = {
            "symbols": {"BTC/USDT": {"1000": 42000.0, "2000": 43000.0}},
            "sources": {},
        }
        since_ms = daily_price_cache_updater_module._compute_fetch_since_ms(
            daily_prices, "BTC/USDT",
        )
        expected_since_ms = int((2000 - commons_constants.DAYS_TO_SECONDS) * 1000)
        assert since_ms == expected_since_ms


class TestIsDailyCacheUpToDate:
    def test_cache_with_today_is_up_to_date(self):
        today_start = daily_price_cache_updater_module._utc_day_start(time.time())
        daily_prices = {
            "symbols": {"BTC/USDT": {str(int(today_start)): 42000.0}},
            "sources": {},
        }
        assert daily_price_cache_updater_module._is_daily_cache_up_to_date(daily_prices, "BTC/USDT") is True

    def test_cache_with_yesterday_is_stale(self):
        yesterday_start = daily_price_cache_updater_module._utc_day_start(time.time()) - 86400
        daily_prices = {
            "symbols": {"BTC/USDT": {str(int(yesterday_start)): 42000.0}},
            "sources": {},
        }
        assert daily_price_cache_updater_module._is_daily_cache_up_to_date(daily_prices, "BTC/USDT") is False


class TestUpdateDailyPrices:
    @pytest.mark.asyncio
    async def test_fetches_and_merges_closes(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
            [172800000, 40500, 42000, 40000, 41000, 200],
        ]

        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )

        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result["symbols"]["BTC/USDT"]["86400"] == 40500
        assert result["symbols"]["BTC/USDT"]["172800"] == 41000
        assert result["sources"]["BTC"] == "BTC/USDT"
        assert "since" not in exchange_manager.exchange.get_symbol_prices.call_args[1]

    @pytest.mark.asyncio
    async def test_empty_cache_fetches_without_since(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )
        assert "since" not in exchange_manager.exchange.get_symbol_prices.call_args[1]

    @pytest.mark.asyncio
    async def test_empty_candles_skips(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = []

        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )

        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result == {"symbols": {}, "sources": {}}

    @pytest.mark.asyncio
    async def test_skips_fetch_when_cache_has_today(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        data_root = str(tmp_path)
        today_start = int(daily_price_cache_updater_module._utc_day_start(time.time()))
        await trading_api.merge_daily_prices(
            "binance", "spot", False, "BTC/USDT", {str(today_start): 42000.0}, data_root,
        )
        await trading_api.set_daily_close_source(
            "binance", "spot", False, "BTC", "BTC/USDT", data_root,
        )

        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )

        exchange_manager.exchange.get_symbol_prices.assert_not_called()

    @pytest.mark.asyncio
    async def test_still_fetches_when_cache_stale(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
        ]
        data_root = str(tmp_path)
        yesterday_start = int(daily_price_cache_updater_module._utc_day_start(time.time()) - 86400)
        await trading_api.merge_daily_prices(
            "binance", "spot", False, "BTC/USDT", {str(yesterday_start): 41000.0}, data_root,
        )
        await trading_api.set_daily_close_source(
            "binance", "spot", False, "BTC", "BTC/USDT", data_root,
        )

        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )

        exchange_manager.exchange.get_symbol_prices.assert_called_once()
        expected_since_ms = int((yesterday_start - commons_constants.DAYS_TO_SECONDS) * 1000)
        assert exchange_manager.exchange.get_symbol_prices.call_args[1]["since"] == expected_since_ms

    @pytest.mark.asyncio
    async def test_stale_cache_with_long_history_uses_newest_not_oldest(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
        ]
        data_root = str(tmp_path)
        yesterday_start = int(daily_price_cache_updater_module._utc_day_start(time.time()) - 86400)
        await trading_api.merge_daily_prices(
            "binance",
            "spot",
            False,
            "BTC/USDT",
            {str(1000): 41000.0, str(yesterday_start): 42000.0},
            data_root,
        )
        await trading_api.set_daily_close_source(
            "binance", "spot", False, "BTC", "BTC/USDT", data_root,
        )

        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
        )

        expected_since_ms = int((yesterday_start - commons_constants.DAYS_TO_SECONDS) * 1000)
        assert exchange_manager.exchange.get_symbol_prices.call_args[1]["since"] == expected_since_ms
        assert exchange_manager.exchange.get_symbol_prices.call_args[1]["since"] != 1000 * 1000

    @pytest.mark.asyncio
    async def test_skips_usd_like_stablecoin_symbol(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["USDC/USDT"])
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "binance", "spot", False, ["USDC/USDT"], data_root,
        )
        exchange_manager.exchange.get_symbol_prices.assert_not_called()

    @pytest.mark.asyncio
    async def test_continues_on_failed_request(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT", "ETH/USDT"])
        exchange_manager.exchange.get_symbol_prices.side_effect = [
            trading_errors.FailedRequest("bingx range error"),
            [[86400000, 40000, 41000, 39000, 40500, 100]],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager,
            "binance",
            "spot",
            False,
            ["BTC/USDT", "ETH/USDT"],
            data_root,
        )
        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result["symbols"]["ETH/USDT"]["86400"] == 40500
        assert "BTC/USDT" not in result["symbols"]

    @pytest.mark.asyncio
    async def test_continues_when_symbol_is_unsupported(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager,
            "binance",
            "spot",
            False,
            ["USDT/USDT", "BTC/USDT"],
            data_root,
        )
        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result["symbols"]["BTC/USDT"]["86400"] == 40500
        assert "USDT/USDT" not in result["symbols"]

    @pytest.mark.asyncio
    async def test_falls_back_to_usd_like_quote(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["KNC/USD"], "kraken")
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 1.0, 1.1, 0.9, 1.05, 100],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "kraken", "spot", False, ["KNC/USDT"], data_root,
        )
        result = await trading_api.load_daily_prices("kraken", "spot", False, data_root)
        assert result["symbols"]["KNC/USD"]["86400"] == 1.05
        assert result["sources"]["KNC"] == "KNC/USD"
        assert trading_api.get_daily_price(result, "KNC/USDT", "86400") == 1.05

    @pytest.mark.asyncio
    async def test_sticky_fetch_symbol_is_tried_first(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["KNC/USD"], "kraken")
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 1.0, 1.1, 0.9, 1.05, 100],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "kraken", "spot", False, ["KNC/USDT"], data_root,
        )
        exchange_manager.client_symbols = ["KNC/USD", "KNC/USDT"]
        exchange_manager.exchange.get_symbol_prices.reset_mock()
        yesterday_start = int(daily_price_cache_updater_module._utc_day_start(time.time()) - 86400)
        await trading_api.merge_daily_prices(
            "kraken", "spot", False, "KNC/USD", {str(yesterday_start): 1.0}, data_root,
        )

        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "kraken", "spot", False, ["KNC/USDT"], data_root,
        )

        exchange_manager.exchange.get_symbol_prices.assert_called_once()
        assert exchange_manager.exchange.get_symbol_prices.call_args[0][0] == "KNC/USD"

    @pytest.mark.asyncio
    async def test_migrates_rows_when_sticky_pair_is_delisted(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["KNC/USDC"], "kraken")
        data_root = str(tmp_path)
        await trading_api.merge_daily_prices(
            "kraken", "spot", False, "KNC/USD", {"86400": 1.0, "172800": 1.1}, data_root,
        )
        await trading_api.set_daily_close_source(
            "kraken", "spot", False, "KNC", "KNC/USD", data_root,
        )
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [259200000, 1.0, 1.1, 0.9, 1.2, 100],
        ]
        exchange_manager.exchange.get_symbol_prices.side_effect = [
            trading_errors.UnSupportedSymbolError("delisted"),
            [[259200000, 1.0, 1.1, 0.9, 1.2, 100]],
        ]

        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "kraken", "spot", False, ["KNC/USDT"], data_root,
        )

        result = await trading_api.load_daily_prices("kraken", "spot", False, data_root)
        assert "KNC/USD" not in result["symbols"]
        assert result["symbols"]["KNC/USDC"]["86400"] == 1.0
        assert result["symbols"]["KNC/USDC"]["172800"] == 1.1
        assert result["symbols"]["KNC/USDC"]["259200"] == 1.2
        assert result["sources"]["KNC"] == "KNC/USDC"

    @pytest.mark.asyncio
    async def test_limited_history_retries_without_since_after_failed_request(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["SOL/USDT"], "bingx")
        exchange_manager.exchange.get_symbol_prices.side_effect = [
            trading_errors.FailedRequest("bingx range error"),
            [[86400000, 40000, 41000, 39000, 40500, 100]],
        ]
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "bingx", "spot", False, ["SOL/USDT"], data_root,
        )

        assert exchange_manager.exchange.get_symbol_prices.call_count == 2
        assert "since" not in exchange_manager.exchange.get_symbol_prices.call_args_list[1][1]
        result = await trading_api.load_daily_prices("bingx", "spot", False, data_root)
        assert result["symbols"]["SOL/USDT"]["86400"] == 40500

    @pytest.mark.asyncio
    async def test_limited_history_logs_error_when_both_attempts_fail(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["SOL/USDT"], "bingx")
        exchange_manager.exchange.get_symbol_prices.side_effect = trading_errors.FailedRequest(
            "bingx range error",
        )
        data_root = str(tmp_path)
        await daily_price_cache_updater_module.update_daily_prices(
            exchange_manager, "bingx", "spot", False, ["SOL/USDT"], data_root,
        )

        assert exchange_manager.exchange.get_symbol_prices.call_count == 2
        result = await trading_api.load_daily_prices("bingx", "spot", False, data_root)
        assert result == {"symbols": {}, "sources": {}}

    @pytest.mark.asyncio
    async def test_full_history_uses_historical_ohlcv_first(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        candles = [[86400000, 40000, 41000, 39000, 40500, 100]]
        data_root = str(tmp_path)
        with _patch_historical_ohlcv(candles=candles):
            await daily_price_cache_updater_module.update_daily_prices(
                exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
            )

        exchange_manager.exchange.get_symbol_prices.assert_not_called()
        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result["symbols"]["BTC/USDT"]["86400"] == 40500

    @pytest.mark.asyncio
    async def test_full_history_falls_back_to_get_symbol_prices(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.return_value = [
            [86400000, 40000, 41000, 39000, 40500, 100],
        ]
        data_root = str(tmp_path)
        with _patch_historical_ohlcv(error=trading_errors.FailedRequest("historical error")):
            await daily_price_cache_updater_module.update_daily_prices(
                exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
            )

        exchange_manager.exchange.get_symbol_prices.assert_called_once()
        assert "since" not in exchange_manager.exchange.get_symbol_prices.call_args[1]
        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result["symbols"]["BTC/USDT"]["86400"] == 40500

    @pytest.mark.asyncio
    async def test_full_history_does_not_use_limited_history_fallback(self, tmp_path):
        exchange_manager = _exchange_manager_with_symbols(["BTC/USDT"])
        exchange_manager.exchange.get_symbol_prices.side_effect = trading_errors.FailedRequest(
            "binance range error",
        )
        data_root = str(tmp_path)
        with _patch_historical_ohlcv(error=trading_errors.FailedRequest("historical error")):
            await daily_price_cache_updater_module.update_daily_prices(
                exchange_manager, "binance", "spot", False, ["BTC/USDT"], data_root,
            )

        exchange_manager.exchange.get_symbol_prices.assert_called_once()
        result = await trading_api.load_daily_prices("binance", "spot", False, data_root)
        assert result == {"symbols": {}, "sources": {}}
