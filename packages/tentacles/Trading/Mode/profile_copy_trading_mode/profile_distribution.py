#  Drakkar-Software OctoBot
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
import decimal
import typing
import datetime
import enum

import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants

if typing.TYPE_CHECKING:
    import tentacles.Services.Services_feeds.exchange_service_feed as exchange_service_feed


class DistributionSource(enum.Enum):
    POSITIONS = "positions"
    PORTFOLIO = "portfolio"


RATIO_PER_ASSET = "ratio_per_asset"
TOTAL_RATIO_PER_ASSET = "total_ratio_per_asset"
INDEXED_COINS = "indexed_coins"
INDEXED_COINS_PRICES = "indexed_coins_prices"
REFERENCE_MARKET_RATIO = "reference_market_ratio"
TRADABLE_RATIO = "tradable_ratio"
DISTRIBUTION_KEY = "distribution"
DISTRIBUTION_SOURCE = "distribution_source"

def get_positions_to_consider(
    profile_positions: list[dict],
    new_position_only: bool,
    started_at: datetime.datetime,
    min_unrealized_pnl_percent: typing.Optional[float] = None,
    max_unrealized_pnl_percent: typing.Optional[float] = None,
    min_mark_price: typing.Optional[decimal.Decimal] = None,
    max_mark_price: typing.Optional[decimal.Decimal] = None
) -> list[dict]:
    result = []
    for position in profile_positions:
        if new_position_only and position.get(trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value) is not None and position.get(trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value, 0) <= started_at.timestamp():
            # skip positions with timestamp at or before started_at (only include strictly after)
            continue

        # Use COLLATERAL or INITIAL_MARGIN as fallback for margin-derived checks (e.g. unrealized pnl ratio)
        margin = decimal.Decimal(str(
            position.get(trading_enums.ExchangeConstantsPositionColumns.COLLATERAL.value)
            or position.get(trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value)
            or 0
        ))

        # Check unrealized pnl ratio only when margin > 0 (otherwise ratio is undefined; include position)
        if margin > decimal.Decimal(0) and (min_unrealized_pnl_percent is not None or max_unrealized_pnl_percent is not None):
            unrealized_pnl = decimal.Decimal(str(position.get(
                trading_enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value, 0
            ) or 0))
            unrealized_pnl_ratio = unrealized_pnl / margin
            if min_unrealized_pnl_percent is not None and unrealized_pnl_ratio < decimal.Decimal(str(min_unrealized_pnl_percent)):
                continue
            if max_unrealized_pnl_percent is not None and unrealized_pnl_ratio > decimal.Decimal(str(max_unrealized_pnl_percent)):
                continue

        # check mark_price
        if min_mark_price is not None or max_mark_price is not None:
            mark_price = decimal.Decimal(str(position.get(
                trading_enums.ExchangeConstantsPositionColumns.MARK_PRICE.value, 0
            ) or 0))
            if min_mark_price is not None and mark_price < min_mark_price:
                continue
            if max_mark_price is not None and mark_price > max_mark_price:
                continue
        result.append(position)
    return result

def get_smoothed_distribution_from_profile_data(
    profile_data: "exchange_service_feed.ExchangeProfile",
    new_position_only: bool,
    started_at: datetime.datetime,
    min_unrealized_pnl_percent: typing.Optional[float] = None,
    max_unrealized_pnl_percent: typing.Optional[float] = None,
    min_mark_price: typing.Optional[decimal.Decimal] = None,
    max_mark_price: typing.Optional[decimal.Decimal] = None
) -> typing.Tuple[typing.List, decimal.Decimal, str]:
    # If profile has positions, use position-based distribution
    if profile_data.positions:
        return _get_distribution_from_positions(
            profile_data, new_position_only, started_at,
            min_unrealized_pnl_percent, max_unrealized_pnl_percent,
            min_mark_price, max_mark_price
        )
    
    # If profile has portfolio but no positions, use portfolio-based distribution
    if profile_data.portfolio is not None:
        return _get_distribution_from_portfolio(profile_data.portfolio)
    
    return [], trading_constants.ZERO, DistributionSource.POSITIONS.value


def _get_distribution_from_positions(
    profile_data: "exchange_service_feed.ExchangeProfile",
    new_position_only: bool,
    started_at: datetime.datetime,
    min_unrealized_pnl_percent: typing.Optional[float] = None,
    max_unrealized_pnl_percent: typing.Optional[float] = None,
    min_mark_price: typing.Optional[decimal.Decimal] = None,
    max_mark_price: typing.Optional[decimal.Decimal] = None
) -> typing.Tuple[typing.List, decimal.Decimal, str]:
    # Calculate total_initial_margin from ALL positions (before filtering)
    total_initial_margin = decimal.Decimal(sum(
        decimal.Decimal(str(position.get(
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value,
            0
        ) or 0))
        for position in profile_data.positions
    ))
    
    if total_initial_margin <= decimal.Decimal(0):
        return [], trading_constants.ZERO, DistributionSource.POSITIONS.value

    tradable_positions: list[dict] = get_positions_to_consider(
        profile_data.positions, new_position_only, started_at,
        min_unrealized_pnl_percent, max_unrealized_pnl_percent, min_mark_price, max_mark_price
    )
    if not tradable_positions:
        return [], trading_constants.ZERO, DistributionSource.POSITIONS.value

    tradable_initial_margin = decimal.Decimal(sum(
        decimal.Decimal(str(position.get(
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value,
            0
        ) or 0))
        for position in tradable_positions
    ))
    
    tradable_ratio = tradable_initial_margin / total_initial_margin

    # Sum initial margins per symbol in case multiple positions exist for the same symbol
    initial_margin_by_coin = {}
    price_by_coin = {}
    for position in tradable_positions:
        symbol = position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value]
        initial_margin = decimal.Decimal(str(position.get(
            trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value,
            0
        ) or 0))
        price_by_coin[symbol] = decimal.Decimal(str(position.get(
            trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value,
            0
        ) or 0))
        if symbol in initial_margin_by_coin:
            initial_margin_by_coin[symbol] += initial_margin
        else:
            initial_margin_by_coin[symbol] = initial_margin
    
    weight_by_coin = {}
    for symbol, initial_margin in initial_margin_by_coin.items():
        weight_by_coin[symbol] = initial_margin / tradable_initial_margin
    
    return index_distribution.get_smoothed_distribution(weight_by_coin, price_by_coin), tradable_ratio, DistributionSource.POSITIONS.value


def _get_distribution_from_portfolio(
    portfolio
) -> typing.Tuple[typing.List, decimal.Decimal, str]:
    if not portfolio.portfolio:
        return [], trading_constants.ZERO, DistributionSource.PORTFOLIO.value
    
    total_value = trading_constants.ZERO
    value_by_asset = {}
    
    for currency, asset in portfolio.portfolio.items():
        total_amount = asset.total
        if total_amount > trading_constants.ZERO:
            value_by_asset[currency] = total_amount
            total_value += total_amount
    
    if total_value <= trading_constants.ZERO:
        return [], trading_constants.ZERO, DistributionSource.PORTFOLIO.value
    
    weight_by_coin = {}
    for currency, value in value_by_asset.items():
        weight_by_coin[currency] = value / total_value
    
    price_by_coin = {}
    return index_distribution.get_smoothed_distribution(weight_by_coin, price_by_coin), trading_constants.ONE, DistributionSource.PORTFOLIO.value


def update_distribution_based_on_profile_data(
    profile_data: "exchange_service_feed.ExchangeProfile",
    distribution_per_exchange_profile: dict[str, dict],
    new_position_only: bool,
    started_at: datetime.datetime,
    min_unrealized_pnl_percent: typing.Optional[float] = None,
    max_unrealized_pnl_percent: typing.Optional[float] = None,
    min_mark_price: typing.Optional[decimal.Decimal] = None,
    max_mark_price: typing.Optional[decimal.Decimal] = None
) -> dict[str, dict]:
    distribution, tradable_ratio, source = get_smoothed_distribution_from_profile_data(
        profile_data, new_position_only, started_at,
        min_unrealized_pnl_percent, max_unrealized_pnl_percent, min_mark_price, max_mark_price
    )
    distribution_per_exchange_profile[profile_data.profile_id] = {
        DISTRIBUTION_KEY: distribution,
        TRADABLE_RATIO: tradable_ratio,
        DISTRIBUTION_SOURCE: source,
    }
    return distribution_per_exchange_profile


def has_distribution_for_all_exchange_profiles(
    distribution_per_exchange_profile: dict[str, dict],
    exchange_profile_ids: list[str]
) -> bool:
    return all(
        profile_id in distribution_per_exchange_profile
        for profile_id in exchange_profile_ids
    )


def update_global_distribution(
    distribution_per_exchange_profile: dict[str, dict],
    per_exchange_profile_portfolio_ratio: decimal.Decimal,
    exchange_profile_ids: list[str],
    allocation_padding_ratio: decimal.Decimal = trading_constants.ZERO
) -> dict:
    merged_ratio_per_asset = {}
    price_weighted_sum_per_asset = {}
    distribution_value_sum_per_asset = {}
    total_effective_allocation = trading_constants.ZERO
    max_profile_allocation = per_exchange_profile_portfolio_ratio * (trading_constants.ONE + allocation_padding_ratio)
    
    for profile_data in distribution_per_exchange_profile.values():
        distribution = profile_data.get(DISTRIBUTION_KEY, [])
        tradable_ratio = profile_data.get(TRADABLE_RATIO, trading_constants.ONE)
        effective_profile_ratio = min(
            per_exchange_profile_portfolio_ratio * tradable_ratio,
            max_profile_allocation
        )
        total_effective_allocation += effective_profile_ratio
        
        ratio_per_asset = {
            asset[index_distribution.DISTRIBUTION_NAME]: asset
            for asset in distribution
        }
        
        for asset_name, asset_dict in ratio_per_asset.items():
            distribution_value = decimal.Decimal(str(asset_dict[index_distribution.DISTRIBUTION_VALUE]))
            weighted_value = distribution_value * effective_profile_ratio
            distribution_price = asset_dict.get(index_distribution.DISTRIBUTION_PRICE)
            
            if asset_name in merged_ratio_per_asset:
                existing_value = decimal.Decimal(str(merged_ratio_per_asset[asset_name][index_distribution.DISTRIBUTION_VALUE]))
                merged_ratio_per_asset[asset_name][index_distribution.DISTRIBUTION_VALUE] = existing_value + weighted_value
            else:
                merged_ratio_per_asset[asset_name] = {
                    index_distribution.DISTRIBUTION_NAME: asset_dict[index_distribution.DISTRIBUTION_NAME],
                    index_distribution.DISTRIBUTION_VALUE: weighted_value
                }
            
            if distribution_price is not None:
                real_price = decimal.Decimal(str(distribution_price))
                if asset_name in price_weighted_sum_per_asset:
                    price_weighted_sum_per_asset[asset_name] += real_price * distribution_value
                    distribution_value_sum_per_asset[asset_name] += distribution_value
                else:
                    price_weighted_sum_per_asset[asset_name] = real_price * distribution_value
                    distribution_value_sum_per_asset[asset_name] = distribution_value
    
    merged_price_per_asset = {}
    for asset_name in price_weighted_sum_per_asset:
        if distribution_value_sum_per_asset[asset_name] > decimal.Decimal(0):
            merged_price_per_asset[asset_name] = price_weighted_sum_per_asset[asset_name] / distribution_value_sum_per_asset[asset_name]
 
    ratio_per_asset = merged_ratio_per_asset
    total_ratio_per_asset = sum(
        decimal.Decimal(str(asset[index_distribution.DISTRIBUTION_VALUE]))
        for asset in ratio_per_asset.values()
    )
    indexed_coins = [
        asset[index_distribution.DISTRIBUTION_NAME]
        for asset in ratio_per_asset.values()
    ]

    reference_market_ratio = max(
        trading_constants.ZERO,
        min(trading_constants.ONE, trading_constants.ONE - total_effective_allocation)
    )
    
    return {
        RATIO_PER_ASSET: ratio_per_asset,
        TOTAL_RATIO_PER_ASSET: total_ratio_per_asset,
        INDEXED_COINS: indexed_coins,
        INDEXED_COINS_PRICES: merged_price_per_asset,
        REFERENCE_MARKET_RATIO: reference_market_ratio,
    }
