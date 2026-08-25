import os

import pytest

import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.databases.market_data_sqlite_database as market_data_sqlite_database_module
import octobot_trading.exchange_data.ticker.persisted_ticker_cache as persisted_ticker_cache


def _empty_latest_tickers():
    return {
        trading_enums.LatestTickersCacheKeys.UPDATED_AT: None,
        trading_enums.LatestTickersCacheKeys.CLOSES: {},
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
        result = await persisted_ticker_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result == _empty_latest_tickers()

    @pytest.mark.asyncio
    async def test_existing_data_loaded(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_ticker_cache.update(
            exchange_name, exchange_type, sandboxed, {"BTC/USDT": 42000.0}, data_root
        )
        result = await persisted_ticker_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result[trading_enums.LatestTickersCacheKeys.CLOSES]["BTC/USDT"] == 42000.0
        assert result[trading_enums.LatestTickersCacheKeys.UPDATED_AT] is not None
        db_path = market_data_sqlite_database_module.MarketDataSQLiteDatabase.get_db_path(
            exchange_name, exchange_type, sandboxed, data_root
        )
        assert os.path.isfile(db_path)
        assert not os.path.isfile(os.path.join(os.path.dirname(db_path), "latest_tickers.json"))


class TestUpdate:
    @pytest.mark.asyncio
    async def test_merge_closes_and_set_updated_at(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_ticker_cache.update(
            exchange_name, exchange_type, sandboxed, {"BTC/USDT": 65000.0}, data_root
        )
        result = await persisted_ticker_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result[trading_enums.LatestTickersCacheKeys.CLOSES]["BTC/USDT"] == 65000.0
        assert result[trading_enums.LatestTickersCacheKeys.UPDATED_AT] is not None

    @pytest.mark.asyncio
    async def test_incremental_update(self, exchange_name, exchange_type, sandboxed, data_root):
        await persisted_ticker_cache.update(
            exchange_name, exchange_type, sandboxed, {"BTC/USDT": 65000.0}, data_root
        )
        await persisted_ticker_cache.update(
            exchange_name, exchange_type, sandboxed, {"ETH/USDT": 3200.0}, data_root
        )
        result = await persisted_ticker_cache.load(exchange_name, exchange_type, sandboxed, data_root)
        assert result[trading_enums.LatestTickersCacheKeys.CLOSES]["BTC/USDT"] == 65000.0
        assert result[trading_enums.LatestTickersCacheKeys.CLOSES]["ETH/USDT"] == 3200.0


class TestGetClose:
    def test_found(self):
        data = {trading_enums.LatestTickersCacheKeys.CLOSES: {"BTC/USDT": 65000.0}}
        assert persisted_ticker_cache.get_close(data, "BTC/USDT") == 65000.0

    def test_missing_returns_default(self):
        data = {trading_enums.LatestTickersCacheKeys.CLOSES: {}}
        assert persisted_ticker_cache.get_close(data, "BTC/USDT", default=0.0) == 0.0
