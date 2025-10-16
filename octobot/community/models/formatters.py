#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import decimal
import typing

import octobot.community.supabase_backend.enums as backend_enums
import octobot.community.supabase_backend as supabase_backend
import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.profiles as commons_profiles
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.api as trading_api


FUTURES_INTERNAL_NAME_SUFFIX = "_futures"
USD_LIKE = "USD-like"


def format_trades(trades: list, exchange_name: str, bot_id: str) -> list:
    return [
        _format_trade(trade, exchange_name, bot_id)
        for trade in trades
        if trade.get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value, None)   # ignore incomplete trades
    ]


def _format_trade(trade: dict, exchange_name: str, bot_id: str):
    metadata = {
        trading_enums.ExchangeConstantsOrderColumns.ENTRIES.value:
            trade[trading_enums.ExchangeConstantsOrderColumns.ENTRIES.value]
    }
    return {
            backend_enums.TradeKeys.BOT_ID.value: bot_id,
            backend_enums.TradeKeys.TRADE_ID.value: trade[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
            or trade[trading_enums.ExchangeConstantsOrderColumns.ID.value],
            backend_enums.TradeKeys.TIME.value: supabase_backend.CommunitySupabaseClient.get_formatted_time(
                trade[trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value]
            ),
            backend_enums.TradeKeys.EXCHANGE.value: exchange_name,
            backend_enums.TradeKeys.PRICE.value: float(trade[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]),
            backend_enums.TradeKeys.QUANTITY.value:
                float(trade[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]),
            backend_enums.TradeKeys.SYMBOL.value: trade[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value],
            backend_enums.TradeKeys.VOLUME.value: float(
                trade.get(trading_enums.ExchangeConstantsOrderColumns.VOLUME.value, 0)
            ),
            backend_enums.TradeKeys.TYPE.value: _get_order_type(trade),
            backend_enums.TradeKeys.BROKER_APPLIED.value: trade[
                trading_enums.ExchangeConstantsOrderColumns.BROKER_APPLIED.value
            ],
            backend_enums.TradeKeys.METADATA.value: metadata
        }


def format_positions(positions: list, exchange_name: str) -> list:
    return [
        {
            # local changes
            backend_enums.PositionKeys.EXCHANGE.value: exchange_name,
            backend_enums.PositionKeys.TIME.value: position[trading_enums.ExchangeConstantsPositionColumns.TIMESTAMP.value],
            backend_enums.PositionKeys.POSITION_ID.value: position[trading_enums.ExchangeConstantsPositionColumns.ID.value],
            # from trading positions
            backend_enums.PositionKeys.LOCAL_ID.value: position[trading_enums.ExchangeConstantsPositionColumns.LOCAL_ID.value],
            backend_enums.PositionKeys.SYMBOL.value: position[trading_enums.ExchangeConstantsPositionColumns.SYMBOL.value],
            backend_enums.PositionKeys.STATUS.value: position[trading_enums.ExchangeConstantsPositionColumns.STATUS.value],
            backend_enums.PositionKeys.SIDE.value: position[trading_enums.ExchangeConstantsPositionColumns.SIDE.value],
            backend_enums.PositionKeys.QUANTITY.value: float(position[trading_enums.ExchangeConstantsPositionColumns.QUANTITY.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.QUANTITY.value] else 0,
            backend_enums.PositionKeys.SIZE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.SIZE.value] else 0,
            backend_enums.PositionKeys.NOTIONAL.value: float(position[trading_enums.ExchangeConstantsPositionColumns.NOTIONAL.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.NOTIONAL.value] else 0,
            backend_enums.PositionKeys.INITIAL_MARGIN.value: float(position[trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value] else 0,
            backend_enums.PositionKeys.AUTO_DEPOSIT_MARGIN.value:
                position[trading_enums.ExchangeConstantsPositionColumns.AUTO_DEPOSIT_MARGIN.value],
            backend_enums.PositionKeys.COLLATERAL.value: float(position[trading_enums.ExchangeConstantsPositionColumns.COLLATERAL.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.COLLATERAL.value] else 0,
            backend_enums.PositionKeys.LEVERAGE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.LEVERAGE.value] else 0,
            backend_enums.PositionKeys.MARGIN_TYPE.value: position[trading_enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value],
            backend_enums.PositionKeys.POSITION_MODE.value: position[trading_enums.ExchangeConstantsPositionColumns.POSITION_MODE.value],
            backend_enums.PositionKeys.ENTRY_PRICE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value] else 0,
            backend_enums.PositionKeys.MARK_PRICE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.MARK_PRICE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.MARK_PRICE.value] else 0,
            backend_enums.PositionKeys.LIQUIDATION_PRICE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value] else 0,
            backend_enums.PositionKeys.UNREALIZED_PNL.value: float(position[trading_enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value] else 0,
            backend_enums.PositionKeys.REALISED_PNL.value: float(position[trading_enums.ExchangeConstantsPositionColumns.REALISED_PNL.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.REALISED_PNL.value] else 0,
            backend_enums.PositionKeys.MAINTENANCE_MARGIN_RATE.value: float(position[trading_enums.ExchangeConstantsPositionColumns.MAINTENANCE_MARGIN_RATE.value])
                if position[trading_enums.ExchangeConstantsPositionColumns.MAINTENANCE_MARGIN_RATE.value] else 0,

        }
        for position in positions
    ]


def format_orders(orders: list, exchange_name: str) -> list:
    return [
        {
            backend_enums.OrderKeys.EXCHANGE.value: exchange_name,
            backend_enums.OrderKeys.SYMBOL.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value],
            backend_enums.OrderKeys.PRICE.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.PRICE.value],
            backend_enums.OrderKeys.TIME.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value],
            backend_enums.OrderKeys.TYPE.value: _get_order_type(
                storage_order[trading_constants.STORAGE_ORIGIN_VALUE]
            ),
            backend_enums.OrderKeys.QUANTITY.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value],
            backend_enums.OrderKeys.FILLED.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.FILLED.value],
            backend_enums.OrderKeys.SIDE.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.SIDE.value],
            backend_enums.OrderKeys.TRIGGER_ABOVE.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE].get(
                trading_enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value
            ),
            backend_enums.OrderKeys.EXCHANGE_ID.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value],
            backend_enums.OrderKeys.REDUCE_ONLY.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value],
            backend_enums.OrderKeys.IS_ACTIVE.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE].get(
                trading_enums.ExchangeConstantsOrderColumns.IS_ACTIVE.value, True),
            backend_enums.OrderKeys.CHAINED.value: format_orders(
                storage_order.get(trading_enums.StoredOrdersAttr.CHAINED_ORDERS.value, []), exchange_name
            ) if storage_order.get(trading_enums.StoredOrdersAttr.CHAINED_ORDERS.value, []) else []
        }
        for storage_order in orders
        if storage_order.get(trading_constants.STORAGE_ORIGIN_VALUE, {}).get(
            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value, None
        )   # ignore incomplete orders
    ]


def _get_order_type(order_or_trade):
    order_type = order_or_trade[trading_enums.ExchangeConstantsOrderColumns.TYPE.value]
    try:
        return trading_personal_data.parse_order_type(order_or_trade)[1].value
    except Exception:
        # use default trade_type
        return order_type


def to_community_exchange_internal_name(bot_exchange_internal_name: str, exchange_type: str) -> str:
    if exchange_type == commons_constants.CONFIG_EXCHANGE_FUTURE:
        return f"{bot_exchange_internal_name}{FUTURES_INTERNAL_NAME_SUFFIX}"
    return bot_exchange_internal_name


def to_bot_exchange_internal_name(community_exchange_internal_name: str) -> str:
    if community_exchange_internal_name.endswith(FUTURES_INTERNAL_NAME_SUFFIX):
        return community_exchange_internal_name[:-len(FUTURES_INTERNAL_NAME_SUFFIX)]
    return community_exchange_internal_name


def create_profile_name(bot_strategy_slug: str, nested_strategy_slug: typing.Optional[str]) -> str:
    if nested_strategy_slug is None:
        return bot_strategy_slug
    return f"{bot_strategy_slug}[{nested_strategy_slug}]"


def get_master_and_nested_product_slug_from_profile_name(profile_name: str) -> (str, typing.Optional[str]):
    nested_product_slug = None
    master_product_slug = profile_name
    if "[" in profile_name and "]" in profile_name:
        # nested product: extract it
        nested_product_slug = profile_name[profile_name.index("[") + 1:profile_name.index("]")]
        master_product_slug = profile_name[:profile_name.index("[")]
    return master_product_slug, nested_product_slug


def ensure_profile_data_exchanges_internal_name_and_type(profile_data: commons_profiles.ProfileData):
    if profile_data.exchanges:
        for exchange_data in profile_data.exchanges:
            exchange_type = get_exchange_type_from_internal_name(exchange_data.internal_name)
            exchange_data.internal_name = to_bot_exchange_internal_name(exchange_data.internal_name)
            exchange_data.exchange_type = exchange_type


def get_exchange_type_from_internal_name(community_exchange_internal_name: str) -> str:
    if community_exchange_internal_name.endswith(FUTURES_INTERNAL_NAME_SUFFIX):
        return commons_constants.CONFIG_EXCHANGE_FUTURE
    return commons_constants.CONFIG_EXCHANGE_SPOT


def get_exchange_type_from_availability(exchange_availability: typing.Optional[dict[str, str]]) -> str:
    if not exchange_availability:
        # use spot by default
        return commons_constants.CONFIG_EXCHANGE_SPOT
    # 1. try futures
    if exchange_availability.get("futures") == backend_enums.ExchangeSupportValues.SUPPORTED.value:
        return commons_constants.CONFIG_EXCHANGE_FUTURE
    # 2. try spot
    if exchange_availability.get("spot") == backend_enums.ExchangeSupportValues.SUPPORTED.value:
        return commons_constants.CONFIG_EXCHANGE_SPOT
    # 3. try market_making
    if exchange_availability.get("market_making") == backend_enums.ExchangeSupportValues.SUPPORTED.value:
        # use SPOT by default, be more accurate later on if necessary
        return commons_constants.CONFIG_EXCHANGE_SPOT
    # 4. something went wrong: select spot and log error
    _get_logger().error(
        f"Unknown exchange type from exchange availability: {exchange_availability}. "
        f"Defaulting to {commons_constants.CONFIG_EXCHANGE_SPOT}"
    )
    return commons_constants.CONFIG_EXCHANGE_SPOT


def format_portfolio(
    current_value: dict, initial_value: dict, profitability: float,
    unit: str, content: dict[str, dict[str, float]], price_by_asset: dict[str, typing.Union[float, decimal.Decimal]],
    bot_id: str, is_sub_portfolio: bool,
    bot_locked_assets: typing.Optional[dict[str, dict[str, decimal.Decimal]]] = None,
) -> dict:
    ref_market_current_value = current_value[unit]
    ref_market_initial_value = initial_value[unit]
    update = {
        backend_enums.PortfolioKeys.CONTENT.value: format_portfolio_content(content, price_by_asset),
        backend_enums.PortfolioKeys.CURRENT_VALUE.value: ref_market_current_value,
        backend_enums.PortfolioKeys.INITIAL_VALUE.value: ref_market_initial_value,
        backend_enums.PortfolioKeys.PROFITABILITY.value: float(profitability),
        backend_enums.PortfolioKeys.UNIT.value: unit,
        backend_enums.PortfolioKeys.BOT_ID.value: bot_id,
        backend_enums.PortfolioKeys.PORTFOLIO_TYPE.value: (
            backend_enums.PortfolioTypes.SUB_PORTFOLIO if is_sub_portfolio
            else backend_enums.PortfolioTypes.FULL_PORTFOLIO
        ).value,
    }
    if bot_locked_assets:
        update[backend_enums.PortfolioKeys.LOCKED_ASSETS.value] = trading_api.format_portfolio(
            bot_locked_assets, False
        )
    return update


def format_portfolio_content(
    content: dict[str, dict[str, float]], price_by_asset: dict[str, typing.Union[float, decimal.Decimal]]
) -> list[dict]:
    return [
        {
            backend_enums.PortfolioAssetKeys.ASSET.value: key,
            backend_enums.PortfolioAssetKeys.QUANTITY.value: float(quantity[commons_constants.PORTFOLIO_TOTAL]),
            backend_enums.PortfolioAssetKeys.VALUE.value:
                float(quantity[commons_constants.PORTFOLIO_TOTAL]) * float(price_by_asset.get(key, 0)),
        }
        for key, quantity in content.items()
    ]


def format_portfolio_with_profitability(profitability) -> dict:
    return {
        backend_enums.PortfolioKeys.PROFITABILITY.value: float(profitability)
    }


def format_portfolio_history(history: dict, unit: str, portfolio_id: str) -> list:
    try:
        return [
            {
                backend_enums.PortfolioHistoryKeys.TIME.value:
                    supabase_backend.CommunitySupabaseClient.get_formatted_time(timestamp),
                backend_enums.PortfolioHistoryKeys.PORTFOLIO_ID.value: portfolio_id,
                backend_enums.PortfolioHistoryKeys.VALUE.value: float(value[unit])
            }
            for timestamp, value in history.items()
            if unit in value and value[unit]    # skip missing a 0 values
        ]
    except KeyError:
        return []


def get_adapted_portfolio(usd_like_asset, portfolio):
    formatted = {}
    for asset in portfolio:
        currency = asset[backend_enums.PortfolioAssetKeys.ASSET.value]
        if currency == USD_LIKE:
            currency = usd_like_asset
        formatted[currency] = asset[backend_enums.PortfolioAssetKeys.VALUE.value]
    return formatted


def get_tentacles_data_exchange_config(
    exchange_internal_name: str, exchange_url: str, config: typing.Optional[dict] = None
) -> commons_profiles.profile_data.TentaclesData:
    try:
        import tentacles.Trading.Exchange as tentacles_exchanges
        return commons_profiles.profile_data.TentaclesData(
            tentacles_exchanges.HollaexAutofilled.get_name(),
            {
                tentacles_exchanges.HollaexAutofilled.AUTO_FILLED_KEY: {
                    exchange_internal_name: {
                        tentacles_exchanges.HollaexAutofilled.URL_KEY: exchange_url
                    }
                }
            } if config is None else config
        )
    except ImportError as err:
        raise ImportError(f"Import tentacles_exchanges failed: {err}")


def _get_logger():
    return commons_logging.get_logger("CommunityFormatter")
