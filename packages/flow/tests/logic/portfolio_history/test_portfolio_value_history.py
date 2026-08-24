import decimal

import pytest

import octobot_flow.logic.portfolio_history.portfolio_value_history as portfolio_value_history_module


def _portfolio(assets: dict[str, float]) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        asset: {"total": decimal.Decimal(str(amount)), "available": decimal.Decimal(str(amount))}
        for asset, amount in assets.items()
    }


class TestComputeDailyPortfolioValues:
    def test_single_day_with_daily_price(self):
        daily_holdings = {
            86400.0: _portfolio({"BTC": 1.0, "USDT": 500.0}),
        }
        daily_prices = {"symbols": {"BTC/USDT": {"86400": 40000.0}}}
        latest_tickers = {"closes": {}}
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, daily_prices, latest_tickers,
        )
        assert len(result) == 1
        assert result[0]["timestamp"] == 86400.0
        assert result[0]["value"] == pytest.approx(40500.0)

    def test_fallback_to_latest_ticker(self):
        daily_holdings = {
            86400.0: _portfolio({"ETH": 2.0}),
        }
        daily_prices = {"symbols": {}}
        latest_tickers = {"closes": {"ETH/USDT": 3000.0}}
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, daily_prices, latest_tickers,
        )
        assert result[0]["value"] == pytest.approx(6000.0)

    def test_reference_market_asset_counted_directly(self):
        daily_holdings = {
            0.0: _portfolio({"USDT": 1000.0}),
        }
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, {"symbols": {}}, {"closes": {}},
        )
        assert result[0]["value"] == pytest.approx(1000.0)

    def test_usd_like_stablecoin_valued_at_face_value(self):
        daily_holdings = {
            0.0: _portfolio({"USDC": 250.0, "USDT": 500.0}),
        }
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, {"symbols": {}}, {"closes": {}},
        )
        assert result[0]["value"] == pytest.approx(750.0)

    def test_missing_price_skips_asset(self):
        daily_holdings = {
            0.0: _portfolio({"UNKNOWN": 100.0, "USDT": 500.0}),
        }
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, {"symbols": {}}, {"closes": {}},
        )
        assert result[0]["value"] == pytest.approx(500.0)

    def test_sorted_ascending(self):
        daily_holdings = {
            172800.0: _portfolio({"USDT": 200.0}),
            86400.0: _portfolio({"USDT": 100.0}),
        }
        result = portfolio_value_history_module.compute_daily_portfolio_values(
            daily_holdings, {"symbols": {}}, {"closes": {}},
        )
        assert result[0]["timestamp"] == 86400.0
        assert result[1]["timestamp"] == 172800.0
