import copy
import datetime
import decimal
import math
import time

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api
import octobot_trading.exchange_data.prices.daily_prices_cache_types as daily_prices_cache_types


def _timestamp_to_datetime(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def _resolve_asset_unit_price(
    asset: str,
    day_timestamp: float,
    day_ts_str: str,
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    latest_tickers: daily_prices_cache_types.LatestTickersCache,
    reference_market: str,
) -> decimal.Decimal | None:
    if asset == reference_market:
        return decimal.Decimal(1)
    if asset in commons_constants.USD_LIKE_COINS:
        return decimal.Decimal(1)

    symbol = f"{asset}/{reference_market}"
    exact_price = trading_api.get_daily_price(daily_prices, symbol, day_ts_str)
    if exact_price is not None:
        return decimal.Decimal(str(exact_price))

    historical_price = trading_api.get_latest_daily_close_on_or_before(
        daily_prices, symbol, day_timestamp,
    )
    if historical_price is not None:
        return decimal.Decimal(str(historical_price))

    if trading_api.get_oldest_daily_price_timestamp(daily_prices, symbol) is not None:
        return None

    ticker_price = trading_api.get_latest_ticker_close(latest_tickers, symbol)
    if ticker_price is not None:
        return decimal.Decimal(str(ticker_price))
    return None


def _value_asset_holding(
    asset: str,
    asset_total: decimal.Decimal,
    day_timestamp: float,
    day_ts_str: str,
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    latest_tickers: daily_prices_cache_types.LatestTickersCache,
    reference_market: str,
) -> decimal.Decimal:
    unit_price = _resolve_asset_unit_price(
        asset,
        day_timestamp,
        day_ts_str,
        daily_prices,
        latest_tickers,
        reference_market,
    )
    if unit_price is None:
        return decimal.Decimal(0)
    return asset_total * unit_price


def _collect_required_valuation_symbols(
    daily_holdings: dict[float, dict[str, dict[str, decimal.Decimal]]],
    reference_market: str,
) -> set[str]:
    required_symbols: set[str] = set()
    for holdings in daily_holdings.values():
        for asset, amounts in holdings.items():
            asset_total = amounts.get("total", decimal.Decimal(0))
            if asset_total == 0:
                continue
            if asset == reference_market or asset in commons_constants.USD_LIKE_COINS:
                continue
            required_symbols.add(f"{asset}/{reference_market}")
    return required_symbols


def _earliest_valuation_timestamp(
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    required_symbols: set[str],
) -> float:
    if not required_symbols:
        return 0.0
    oldest_timestamps = []
    for symbol in required_symbols:
        oldest_timestamp = trading_api.get_oldest_daily_price_timestamp(daily_prices, symbol)
        if oldest_timestamp is not None:
            oldest_timestamps.append(oldest_timestamp)
    if not oldest_timestamps:
        return 0.0
    return max(oldest_timestamps)


def _utc_day_start(timestamp: float) -> float:
    return float(math.floor(
        timestamp / commons_constants.DAYS_TO_SECONDS
    ) * commons_constants.DAYS_TO_SECONDS)


def _expand_sparse_daily_holdings(
    daily_holdings: dict[float, dict[str, dict[str, decimal.Decimal]]],
    start_day_timestamp: float,
    end_day_timestamp: float,
) -> dict[float, dict[str, dict[str, decimal.Decimal]]]:
    if start_day_timestamp > end_day_timestamp or not daily_holdings:
        return {}

    sparse_days = sorted(daily_holdings)
    dense_holdings: dict[float, dict[str, dict[str, decimal.Decimal]]] = {}
    sparse_day_index = 0
    current_holdings = None

    day_timestamp = start_day_timestamp
    while day_timestamp <= end_day_timestamp:
        while (
            sparse_day_index < len(sparse_days)
            and sparse_days[sparse_day_index] <= day_timestamp
        ):
            current_holdings = copy.deepcopy(daily_holdings[sparse_days[sparse_day_index]])
            sparse_day_index += 1
        if current_holdings is not None:
            dense_holdings[day_timestamp] = current_holdings
        day_timestamp += commons_constants.DAYS_TO_SECONDS

    return dense_holdings


def _build_day_assets_protocol(
    day_assets: list[protocol_models.HistoricalAssetValue],
) -> list[protocol_models.HistoricalAssetsForTradingType] | None:
    if not day_assets:
        return None
    return [
        protocol_models.HistoricalAssetsForTradingType(
            trading_type=protocol_models.TradingType.SPOT,
            assets=day_assets,
        )
    ]


def compute_daily_portfolio_values(
    daily_holdings: dict[float, dict[str, dict[str, decimal.Decimal]]],
    daily_prices: daily_prices_cache_types.DailyPricesCache,
    latest_tickers: daily_prices_cache_types.LatestTickersCache,
    reference_market: str = "USDT",
) -> list[protocol_models.PortfolioHistoricalValue]:
    """
    Value daily portfolio holdings using daily price cache with historical
    fallback, then latest ticker only when no historical closes exist.

    Returns one valued point per UTC calendar day within the candle coverage
    window. Sparse trade-replay holdings are forward-filled on quiet days so
    daily price moves are reflected even without transactions.

    Days before the global candle coverage window are omitted. Assets that
    cannot be priced contribute value 0 but remain in the breakdown.

    Returns protocol models sorted ascending by timestamp.
    """
    if not daily_holdings:
        return []

    required_symbols = _collect_required_valuation_symbols(daily_holdings, reference_market)
    earliest_valuation_timestamp = _earliest_valuation_timestamp(daily_prices, required_symbols)

    end_day_timestamp = _utc_day_start(time.time())
    valuation_start_timestamp = earliest_valuation_timestamp
    if valuation_start_timestamp == 0.0:
        valuation_start_timestamp = min(daily_holdings)
    valuation_start_timestamp = _utc_day_start(valuation_start_timestamp)
    dense_holdings = _expand_sparse_daily_holdings(
        daily_holdings,
        valuation_start_timestamp,
        end_day_timestamp,
    )

    valued_days: list[protocol_models.PortfolioHistoricalValue] = []
    for day_timestamp in sorted(dense_holdings):
        holdings = dense_holdings[day_timestamp]
        total_value = decimal.Decimal(0)
        day_assets: list[protocol_models.HistoricalAssetValue] = []
        day_ts_str = str(int(day_timestamp))

        for asset, amounts in holdings.items():
            asset_total = amounts.get("total", decimal.Decimal(0))
            if asset_total == 0:
                continue

            asset_value = _value_asset_holding(
                asset,
                asset_total,
                day_timestamp,
                day_ts_str,
                daily_prices,
                latest_tickers,
                reference_market,
            )
            total_value += asset_value
            day_assets.append(
                protocol_models.HistoricalAssetValue(
                    symbol=asset,
                    holdings=float(asset_total),
                    value=float(asset_value),
                )
            )

        valued_days.append(
            protocol_models.PortfolioHistoricalValue(
                timestamp=_timestamp_to_datetime(day_timestamp),
                total=float(total_value),
                assets=_build_day_assets_protocol(day_assets),
            )
        )

    return valued_days
