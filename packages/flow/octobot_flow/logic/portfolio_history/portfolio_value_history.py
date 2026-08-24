import decimal

import octobot_commons.constants as commons_constants
import octobot_trading.api as trading_api


def compute_daily_portfolio_values(
    daily_holdings: dict[float, dict[str, dict[str, decimal.Decimal]]],
    daily_prices: dict,
    latest_tickers: dict,
    reference_market: str = "USDT",
) -> list[dict]:
    """
    Value daily portfolio holdings using daily price cache, falling back to
    latest ticker prices when a historical price is unavailable.

    Returns a list of dicts with 'timestamp' and 'value' keys, sorted ascending.
    """
    valued_days = []
    for day_timestamp in sorted(daily_holdings):
        holdings = daily_holdings[day_timestamp]
        total_value = decimal.Decimal(0)
        day_ts_str = str(int(day_timestamp))

        for asset, amounts in holdings.items():
            asset_total = amounts.get("total", decimal.Decimal(0))
            if asset_total == 0:
                continue

            if asset == reference_market:
                total_value += asset_total
                continue

            if asset in commons_constants.USD_LIKE_COINS:
                total_value += asset_total
                continue

            symbol = f"{asset}/{reference_market}"
            price = trading_api.get_daily_price(daily_prices, symbol, day_ts_str)
            if price is None:
                price = trading_api.get_latest_ticker_close(latest_tickers, symbol)
            if price is not None:
                total_value += asset_total * decimal.Decimal(str(price))

        valued_days.append({
            "timestamp": day_timestamp,
            "value": float(total_value),
        })

    return valued_days
