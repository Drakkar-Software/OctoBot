import os

import pytest

import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module
import octobot_trading.exchange_data.prices.persisted_price_cache as persisted_price_cache


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
        assert result == {"symbols": {}, "sources": {}}

    @pytest.mark.asyncio
    async def test_existing_data_loaded(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"1704067200": 42000.0}, data_root
        )
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result == {"symbols": {"BTC/USDT": {"1704067200": 42000.0}}, "sources": {}}
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
        assert result["symbols"]["BTC/USDT"] == {"1000": 50000.0, "2000": 51000.0}

    @pytest.mark.asyncio
    async def test_incremental_merge(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"1000": 50000.0}, data_root
        )
        await persisted_price_cache.merge_closes(
            exchange_name, exchange_type, sandboxed, "BTC/USDT", {"2000": 51000.0}, data_root
        )
        result = await persisted_price_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result["symbols"]["BTC/USDT"] == {"1000": 50000.0, "2000": 51000.0}


class TestOldestTimestamp:
    def test_empty_returns_none(self):
        assert persisted_price_cache.oldest_timestamp({"symbols": {}}, "BTC/USDT") is None

    def test_returns_minimum(self):
        data = {"symbols": {"BTC/USDT": {"2000": 1.0, "1000": 2.0, "3000": 3.0}}}
        assert persisted_price_cache.oldest_timestamp(data, "BTC/USDT") == 1000.0


class TestNewestTimestamp:
    def test_empty_returns_none(self):
        assert persisted_price_cache.newest_timestamp({"symbols": {}}, "BTC/USDT") is None

    def test_returns_maximum(self):
        data = {"symbols": {"BTC/USDT": {"2000": 1.0, "1000": 2.0, "3000": 3.0}}}
        assert persisted_price_cache.newest_timestamp(data, "BTC/USDT") == 3000.0


class TestGetClose:
    def test_found(self):
        data = {"symbols": {"BTC/USDT": {"1000": 42000.0}}, "sources": {}}
        assert persisted_price_cache.get_close(data, "BTC/USDT", "1000") == 42000.0

    def test_missing_returns_default(self):
        data = {"symbols": {}, "sources": {}}
        assert persisted_price_cache.get_close(data, "BTC/USDT", "1000", default=-1.0) == -1.0

    def test_resolves_reference_symbol_via_source_mapping(self):
        data = {
            "symbols": {"KNC/USD": {"1000": 1.05}},
            "sources": {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.get_close(data, "KNC/USDT", "1000") == 1.05


class TestResolveSymbolTimestamps:
    def test_oldest_timestamp_uses_source_mapping(self):
        data = {
            "symbols": {"KNC/USD": {"1000": 1.0, "2000": 1.1}},
            "sources": {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.oldest_timestamp(data, "KNC/USDT") == 1000.0

    def test_newest_timestamp_uses_source_mapping(self):
        data = {
            "symbols": {"KNC/USD": {"1000": 1.0, "2000": 1.1}},
            "sources": {"KNC": "KNC/USD"},
        }
        assert persisted_price_cache.newest_timestamp(data, "KNC/USDT") == 2000.0
