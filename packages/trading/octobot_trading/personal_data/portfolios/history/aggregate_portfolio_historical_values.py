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

import octobot_commons.timestamp_util as timestamp_util_module
import octobot_protocol.models as protocol_models

import octobot_trading.personal_data.portfolios.history.daily_portfolio_value_history as daily_portfolio_value_history_module


def _iter_historical_assets(
    history_value: protocol_models.PortfolioHistoricalValue,
):
    if not history_value.assets:
        return
    for assets_for_type in history_value.assets:
        for asset in assets_for_type.assets or []:
            yield assets_for_type.trading_type, asset


def aggregate_portfolio_historical_values(
    account_histories: list[list[protocol_models.PortfolioHistoricalValue]],
) -> list[protocol_models.PortfolioHistoricalValue]:
    totals_by_day: dict[float, float] = {}
    assets_by_day: dict[float, dict[protocol_models.TradingType, dict[str, list[float]]]] = {}
    for history_values in account_histories:
        for history_value in history_values:
            day_key = daily_portfolio_value_history_module.utc_day_start(
                history_value.timestamp.timestamp(),
            )
            totals_by_day[day_key] = totals_by_day.get(day_key, 0.0) + float(history_value.total)
            day_assets = assets_by_day.setdefault(day_key, {})
            for trading_type, asset in _iter_historical_assets(history_value):
                symbol_totals = day_assets.setdefault(trading_type, {})
                holdings_sum, value_sum = symbol_totals.get(asset.symbol, [0.0, 0.0])
                symbol_totals[asset.symbol] = [
                    holdings_sum + float(asset.holdings),
                    value_sum + float(asset.value),
                ]

    aggregated_values: list[protocol_models.PortfolioHistoricalValue] = []
    for day_key in sorted(totals_by_day):
        assets_for_day = assets_by_day.get(day_key, {})
        assets_by_trading_type: list[protocol_models.HistoricalAssetsForTradingType] = []
        for trading_type in sorted(assets_for_day, key=lambda trading_type_value: trading_type_value.value):
            symbol_totals = assets_for_day[trading_type]
            day_asset_values: list[protocol_models.HistoricalAssetValue] = []
            for symbol, holdings_and_value in sorted(symbol_totals.items()):
                holdings_sum, value_sum = holdings_and_value
                if holdings_sum == 0:
                    continue
                day_asset_values.append(
                    protocol_models.HistoricalAssetValue(
                        symbol=symbol,
                        holdings=holdings_sum,
                        value=value_sum,
                    )
                )
            if day_asset_values:
                assets_by_trading_type.append(
                    protocol_models.HistoricalAssetsForTradingType(
                        trading_type=trading_type,
                        assets=day_asset_values,
                    )
                )
        aggregated_values.append(
            protocol_models.PortfolioHistoricalValue(
                timestamp=timestamp_util_module.utc_datetime_from_timestamp(day_key),
                total=totals_by_day[day_key],
                assets=assets_by_trading_type or None,
            )
        )
    return aggregated_values
