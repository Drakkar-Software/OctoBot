#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
import octobot.community.supabase_backend.enums as backend_enums
import octobot.community.supabase_backend as supabase_backend
import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data


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
            backend_enums.OrderKeys.EXCHANGE_ID.value: storage_order[trading_constants.STORAGE_ORIGIN_VALUE][
                trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value],
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


def format_portfolio(
    current_value: dict, initial_value: dict, profitability: float,
    unit: str, content: dict, price_by_asset: dict,
    bot_id: str
) -> dict:
    ref_market_current_value = current_value[unit]
    ref_market_initial_value = initial_value[unit]
    formatted_content = [
        {
            backend_enums.PortfolioAssetKeys.ASSET.value: key,
            backend_enums.PortfolioAssetKeys.QUANTITY.value: float(quantity[commons_constants.PORTFOLIO_TOTAL]),
            backend_enums.PortfolioAssetKeys.VALUE.value:
                float(quantity[commons_constants.PORTFOLIO_TOTAL]) * float(price_by_asset.get(key, 0)),
        }
        for key, quantity in content.items()
    ]

    return {
        backend_enums.PortfolioKeys.CONTENT.value: formatted_content,
        backend_enums.PortfolioKeys.CURRENT_VALUE.value: ref_market_current_value,
        backend_enums.PortfolioKeys.INITIAL_VALUE.value: ref_market_initial_value,
        backend_enums.PortfolioKeys.PROFITABILITY.value: float(profitability),
        backend_enums.PortfolioKeys.UNIT.value: unit,
        backend_enums.PortfolioKeys.BOT_ID.value: bot_id,
    }


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
        if currency == "USD-like":
            currency = usd_like_asset
        formatted[currency] = asset[backend_enums.PortfolioAssetKeys.VALUE.value]
    return formatted
