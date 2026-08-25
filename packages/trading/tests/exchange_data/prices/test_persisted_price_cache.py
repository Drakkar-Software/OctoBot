import os

import pytest

import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module
import octobot_trading.exchange_data.prices.persisted_price_cache as persisted_price_cache


def _empty_daily_prices():
    return {
        trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
        trading_enums.DailyPricesCacheKeys.SOURCES: {},
    }


@pytest.fixture
def data_root(tmp_path):
    return str(tmp_path)


@pytest.fixture
def exchange_name():
    return "binance"


@pytest.fixture
def exchange_type():
    return "spot"


@pytest.fixture
def sandboxed():
    return False


class TestLoad:
    @pytest.mark.asyncio
    async def test_missing_database_returns_empty(self, exchange_name, exchange_type, sandboxed, data_root):
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result == _empty_daily_prices()

    @pytest.mark.asyncio
    async def test_existing_data_loaded(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"1704067200": 42000.0}, data_root
        )
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result == {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1704067200": 42000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            exchange_name, exchange_type, sandboxed, data_root
        )
        assert os.path.isfile(db_path)
        assert not os.path.isfile(os.path.join(os.path.dirname(db_path), "daily_prices.json"))


class TestMergeCloses:
    @pytest.mark.asyncio
    async def test_merge_into_empty(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"1000": 50000.0, "2000": 51000.0}, data_root
        )
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 50000.0, "2000": 51000.0}

    @pytest.mark.asyncio
    async def test_incremental_merge(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"1000": 50000.0}, data_root
        )
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"2000": 51000.0}, data_root
        )
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 50000.0, "2000": 51000.0}


class TestOldestTimestamp:
    def test_empty_returns_none(self):
        assert persisted_price_cache.oldest_timestamp(_empty_daily_prices(), "BTC/USDT") is None

    def test_returns_minimum(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 1.0, "1000": 2.0, "3000": 3.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert persisted_price_cache.oldest_timestamp(data, "BTC/USDT") == 1000.0


class TestNewestTimestamp:
    def test_empty_returns_none(self):
        assert persisted_price_cache.newest_timestamp(_empty_daily_prices(), "BTC/USDT") is None

    def test_returns_maximum(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"2000": 1.0, "1000": 2.0, "3000": 3.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert persisted_price_cache.newest_timestamp(data, "BTC/USDT") == 3000.0


class TestGetClose:
    def test_found(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1000": 42000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert persisted_price_cache.get_close(data, "BTC/USDT", "1000") == 42000.0

    def test_missing_returns_default(self):
        assert persisted_price_cache.get_close(_empty_daily_prices(), "BTC/USDT", "1000", default=-1.0) == -1.0

    def test_resolves_reference_symbol_via_source_mapping(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"KNC/USD": {"1000": 1.05}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.get_close(data, "KNC/USDT", "1000") == 1.05


class TestLatestCloseOnOrBefore:
    def test_returns_latest_close_on_or_before_day(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {
                "BTC/USDT": {
                    "86400": 40000.0,
                    "172800": 41000.0,
                }
            },
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert persisted_price_cache.latest_close_on_or_before(
            data, "BTC/USDT", 200000.0,
        ) == 41000.0

    def test_returns_none_when_no_close_on_or_before_day(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"172800": 41000.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        assert persisted_price_cache.latest_close_on_or_before(
            data, "BTC/USDT", 86400.0,
        ) is None


class TestMoveSymbolClosesInMemory:
    def test_moves_closes_to_new_symbol(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"OLD/USDT": {"1000": 1.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        persisted_price_cache.move_symbol_closes_in_memory(data, "OLD/USDT", "NEW/USDT")
        assert "OLD/USDT" not in data[trading_enums.DailyPricesCacheKeys.SYMBOLS]
        assert data[trading_enums.DailyPricesCacheKeys.SYMBOLS]["NEW/USDT"] == {"1000": 1.0}


class TestGetCloseSource:
    def test_returns_none_when_missing(self):
        assert persisted_price_cache.get_close_source(_empty_daily_prices(), "BTC") is None

    def test_returns_mapped_symbol(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.get_close_source(data, "KNC") == "KNC/USD"


class TestSetCloseSourceInMemory:
    def test_sets_source_mapping(self):
        data = _empty_daily_prices()
        persisted_price_cache.set_close_source_in_memory(data, "BTC", "BTC/USDT")
        assert data[trading_enums.DailyPricesCacheKeys.SOURCES]["BTC"] == "BTC/USDT"


class TestMergeSymbolClosesInMemory:
    def test_merges_closes_for_symbol(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"BTC/USDT": {"1000": 1.0}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {},
        }
        persisted_price_cache.merge_symbol_closes_in_memory(
            data, "BTC/USDT", {"2000": 2.0},
        )
        assert data[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 1.0, "2000": 2.0}

    def test_creates_symbol_entry_when_missing(self):
        data = _empty_daily_prices()
        persisted_price_cache.merge_symbol_closes_in_memory(
            data, "BTC/USDT", {"1000": 1.0},
        )
        assert data[trading_enums.DailyPricesCacheKeys.SYMBOLS]["BTC/USDT"] == {"1000": 1.0}


class TestResolveSymbolTimestamps:
    def test_oldest_timestamp_uses_source_mapping(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"KNC/USD": {"1000": 1.0, "2000": 1.1}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.oldest_timestamp(data, "KNC/USDT") == 1000.0

    def test_newest_timestamp_uses_source_mapping(self):
        data = {
            trading_enums.DailyPricesCacheKeys.SYMBOLS: {"KNC/USD": {"1000": 1.0, "2000": 1.1}},
            trading_enums.DailyPricesCacheKeys.SOURCES: {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.newest_timestamp(data, "KNC/USDT") == 2000.0
