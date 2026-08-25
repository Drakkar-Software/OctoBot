import datetime
import decimal
from contextlib import contextmanager

import mock
import pytest

import octobot_flow.logic.portfolio_history.portfolio_value_history as portfolio_value_history_module
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types


def _portfolio(assets: dict[str, float]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        asset: {"total": decimal.Decimal(str(amount)), "available": decimal.Decimal(str(amount))}
        for asset, amount in assets.items()
    }


def _empty_tickers() -> daily_prices_cache_types.LatestTickersCache:
    return daily_prices_cache_types.empty_latest_tickers_cache()


def _daily_prices(symbols: dict[str, dict[str, float]]) -> daily_prices_cache_types.DailyPricesCache:
    return {
        trading_enums.DailyPricesCacheKeys.SYMBOLS: symbols,
        trading_enums.DailyPricesCacheKeys.SOURCES: {},
    }


def _tickers(closes: dict[str, float]) -> daily_prices_cache_types.LatestTickersCache:
    return {
        trading_enums.LatestTickersCacheKeys.UPDATED_AT: None,
        trading_enums.LatestTickersCacheKeys.CLOSES: closes,
    }


@contextmanager
def _with_end_day(end_day_timestamp: float):
    with mock.patch.object(
        portfolio_value_history_module.time,
        "time",
        return_value=end_day_timestamp,
    ):
        yield


def _compute_values(
    daily_holdings,
    daily_prices,
    latest_tickers,
    *,
    end_day_timestamp: float,
    reference_market: str = "USDT",
):
    with _with_end_day(end_day_timestamp):
        return portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings,
            daily_prices,
            latest_tickers,
            reference_market=reference_market,
        )


def _spot_assets(history_value) -> list:
    assert history_value.assets is not None
    return history_value.assets[0].assets


def _asset_by_symbol(day_assets, symbol: str):
    for asset_entry in day_assets:
        if asset_entry.symbol == symbol:
            return asset_entry
    raise AssertionError(f"Asset {symbol} not found in {day_assets}")


class TestExpandSparseDailyHoldings:
    def test_forward_fills_holdings_between_sparse_days(self):
        sparse_holdings = {
            86400.0: _portfolio({"BTC": 1.0}),
            259200.0: _portfolio({"BTC": 2.0}),
        }

        dense_holdings = portfolio_value_history_module._expand_sparse_daily_holdings(
            sparse_holdings, 86400.0, 259200.0,
        )

        assert list(dense_holdings) == [86400.0, 172800.0, 259200.0]
        assert dense_holdings[172800.0]["BTC"]["total"] == decimal.Decimal("1")


class TestEarliestValuationTimestamp:
    def test_returns_max_oldest_timestamp_across_symbols(self):
        daily_prices = _daily_prices({
            "BTC/USDT": {"86400": 1.0},
            "ETH/USDT": {"172800": 1.0},
        })
        required_symbols = {"BTC/USDT", "ETH/USDT"}
        result = portfolio_value_history_module._earliest_valuation_timestamp(
            daily_prices, required_symbols,
        )
        assert result == 172800.0

    def test_returns_zero_when_no_required_symbols(self):
        result = portfolio_value_history_module._earliest_valuation_timestamp(
            _daily_prices({}), set(),
        )
        assert result == 0.0


class TestResolveAssetUnitPrice:
    def test_uses_ticker_only_when_no_historical_closes_exist(self):
        daily_prices = _daily_prices({})
        latest_tickers = _tickers({"ETH/USDT": 3000.0})
        result = portfolio_value_history_module._resolve_asset_unit_price(
            "ETH", 86400.0, "86400", daily_prices, latest_tickers, "USDT",
        )
        assert result == decimal.Decimal("3000")

    def test_does_not_use_ticker_when_historical_exists_but_not_on_day(self):
        daily_prices = _daily_prices({"ETH/USDT": {"172800": 2500.0}})
        latest_tickers = _tickers({"ETH/USDT": 3000.0})
        result = portfolio_value_history_module._resolve_asset_unit_price(
            "ETH", 86400.0, "86400", daily_prices, latest_tickers, "USDT",
        )
        assert result is None


class TestComputeDailyPortfolioValues:
    def test_single_day_with_daily_price(self):
        daily_holdings = {
            86400.0: _portfolio({"BTC": 1.0, "USDT": 500.0}),
        }
        daily_prices = _daily_prices({"BTC/USDT": {"86400": 40000.0}})
        result = _compute_values(
            daily_holdings, daily_prices, _empty_tickers(), end_day_timestamp=86400.0,
        )
        assert len(result) == 1
        assert result[0].timestamp == datetime.datetime.fromtimestamp(86400.0, tz=datetime.timezone.utc)
        assert result[0].total == pytest.approx(40500.0)

    def test_fallback_to_latest_ticker_when_no_historical_closes(self):
        daily_holdings = {
            86400.0: _portfolio({"ETH": 2.0}),
        }
        result = _compute_values(
            daily_holdings,
            _daily_prices({}),
            _tickers({"ETH/USDT": 3000.0}),
            end_day_timestamp=86400.0,
        )
        assert result[0].total == pytest.approx(6000.0)

    def test_reference_market_asset_counted_directly(self):
        daily_holdings = {
            0.0: _portfolio({"USDT": 1000.0}),
        }
        result = _compute_values(
            daily_holdings, _daily_prices({}), _empty_tickers(), end_day_timestamp=0.0,
        )
        assert result[0].total == pytest.approx(1000.0)

    def test_usd_like_stablecoin_valued_at_face_value(self):
        daily_holdings = {
            0.0: _portfolio({"USDC": 250.0, "USDT": 500.0}),
        }
        result = _compute_values(
            daily_holdings, _daily_prices({}), _empty_tickers(), end_day_timestamp=0.0,
        )
        assert result[0].total == pytest.approx(750.0)

    def test_unpriced_asset_has_zero_value_but_remains_in_breakdown(self):
        daily_holdings = {
            0.0: _portfolio({"UNKNOWN": 100.0, "USDT": 500.0}),
        }
        result = _compute_values(
            daily_holdings, _daily_prices({}), _empty_tickers(), end_day_timestamp=0.0,
        )
        assert result[0].total == pytest.approx(500.0)

    def test_sorted_ascending(self):
        daily_holdings = {
            172800.0: _portfolio({"USDT": 200.0}),
            86400.0: _portfolio({"USDT": 100.0}),
        }
        result = _compute_values(
            daily_holdings, _daily_prices({}), _empty_tickers(), end_day_timestamp=172800.0,
        )
        assert len(result) == 2
        assert result[0].timestamp == datetime.datetime.fromtimestamp(86400.0, tz=datetime.timezone.utc)
        assert result[1].timestamp == datetime.datetime.fromtimestamp(172800.0, tz=datetime.timezone.utc)

    def test_zero_holding_asset_omitted_from_assets(self):
        daily_holdings = {
            0.0: _portfolio({"BTC": 0.0, "USDT": 100.0}),
        }
        result = _compute_values(
            daily_holdings, _daily_prices({}), _empty_tickers(), end_day_timestamp=0.0,
        )
        assert {asset_entry.symbol for asset_entry in _spot_assets(result[0])} == {"USDT"}

    def test_excludes_days_before_global_candle_cutoff(self):
        daily_holdings = {
            86400.0: _portfolio({"BTC": 1.0}),
            172800.0: _portfolio({"BTC": 1.0}),
        }
        daily_prices = _daily_prices({"BTC/USDT": {"172800": 50000.0}})
        result = _compute_values(
            daily_holdings, daily_prices, _empty_tickers(), end_day_timestamp=172800.0,
        )
        assert len(result) == 1
        assert result[0].timestamp == datetime.datetime.fromtimestamp(172800.0, tz=datetime.timezone.utc)

    def test_uses_historical_close_when_exact_day_missing(self):
        daily_holdings = {
            172800.0: _portfolio({"ETH": 2.0}),
        }
        daily_prices = _daily_prices({"ETH/USDT": {"86400": 2000.0}})
        result = _compute_values(
            daily_holdings,
            daily_prices,
            _tickers({"ETH/USDT": 9999.0}),
            end_day_timestamp=172800.0,
        )
        assert result[0].total == pytest.approx(4000.0)

    def test_forward_fills_quiet_days_and_reprices_daily(self):
        day_a = 86400.0
        day_b = 172800.0
        day_c = 259200.0
        daily_holdings = {
            day_a: _portfolio({"BTC": 1.0}),
            day_c: _portfolio({"BTC": 1.0}),
        }
        daily_prices = _daily_prices({
            "BTC/USDT": {
                str(int(day_a)): 40000.0,
                str(int(day_b)): 45000.0,
                str(int(day_c)): 50000.0,
            },
        })
        result = _compute_values(
            daily_holdings, daily_prices, _empty_tickers(), end_day_timestamp=day_c,
        )
        assert len(result) == 3
        assert result[1].total == pytest.approx(45000.0)

    def test_returns_empty_for_empty_sparse_holdings(self):
        result = _compute_values(
            {}, _daily_prices({"BTC/USDT": {"86400": 1.0}}), _empty_tickers(), end_day_timestamp=86400.0,
        )
        assert result == []

    def test_excludes_ancient_day_even_when_ticker_exists(self):
        daily_holdings = {
            86400.0: _portfolio({"BTC": 1.0}),
            259200.0: _portfolio({"BTC": 1.0}),
        }
        daily_prices = _daily_prices({"BTC/USDT": {"172800": 42000.0}})
        result = _compute_values(
            daily_holdings,
            daily_prices,
            _tickers({"BTC/USDT": 90000.0}),
            end_day_timestamp=259200.0,
        )
        assert len(result) == 2
        assert result[0].timestamp == datetime.datetime.fromtimestamp(172800.0, tz=datetime.timezone.utc)
        assert result[0].total == pytest.approx(42000.0)
        assert result[1].timestamp == datetime.datetime.fromtimestamp(259200.0, tz=datetime.timezone.utc)
        assert result[1].total == pytest.approx(42000.0)

    def test_excludes_pre_candle_trade_days_using_dynamic_cutoff(self):
        ancient_trade_day = 1546300800.0  # 2019-01-01 UTC
        candle_oldest_day = 1725321600.0  # 2024-09-03 UTC
        recent_day = candle_oldest_day + 86400.0
        daily_holdings = {
            ancient_trade_day: _portfolio({"BTC": 1.0}),
            candle_oldest_day: _portfolio({"BTC": 1.0}),
            recent_day: _portfolio({"BTC": 1.0}),
        }
        daily_prices = _daily_prices({
            "BTC/USDT": {
                str(int(candle_oldest_day)): 50000.0,
                str(int(recent_day)): 51000.0,
            },
        })
        result = _compute_values(
            daily_holdings, daily_prices, _empty_tickers(), end_day_timestamp=recent_day,
        )
        assert len(result) == 2
        assert result[0].timestamp == datetime.datetime.fromtimestamp(
            candle_oldest_day, tz=datetime.timezone.utc,
        )
        assert result[1].timestamp == datetime.datetime.fromtimestamp(
            recent_day, tz=datetime.timezone.utc,
        )

    def test_emits_utc_midnight_timestamps_when_candle_cache_starts_mid_day(self):
        day_one_midnight = 86400.0
        day_one_sixteen_hundred = day_one_midnight + 57600.0
        day_two_midnight = 172800.0
        daily_holdings = {
            day_one_midnight: _portfolio({"BTC": 1.0}),
            day_two_midnight: _portfolio({"BTC": 1.0}),
        }
        daily_prices = _daily_prices({
            "BTC/USDT": {
                str(int(day_one_sixteen_hundred)): 40000.0,
                str(int(day_two_midnight)): 50000.0,
            },
        })
        result = _compute_values(
            daily_holdings,
            daily_prices,
            _empty_tickers(),
            end_day_timestamp=day_two_midnight,
        )
        assert len(result) == 2
        assert result[0].timestamp == datetime.datetime.fromtimestamp(
            day_one_midnight, tz=datetime.timezone.utc,
        )
        assert result[1].timestamp == datetime.datetime.fromtimestamp(
            day_two_midnight, tz=datetime.timezone.utc,
        )
        assert result[1].total == pytest.approx(50000.0)
