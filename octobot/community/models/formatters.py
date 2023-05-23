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


def format_trades(trades, bot_id) -> list:
    return [
        {
            backend_enums.TradeKeys.BOT_ID.value: bot_id,
            backend_enums.TradeKeys.TRADE_ID.value: trade.trade_id,
            backend_enums.TradeKeys.TIME.value:
                supabase_backend.CommunitySupabaseClient.get_formatted_time(trade.executed_time),
            backend_enums.TradeKeys.EXCHANGE.value: trade.exchange_manager.exchange_name,
            backend_enums.TradeKeys.PRICE.value: float(trade.executed_price),
            backend_enums.TradeKeys.QUANTITY.value: float(trade.executed_quantity),
            backend_enums.TradeKeys.SYMBOL.value: trade.symbol,
            backend_enums.TradeKeys.TYPE.value: trade.trade_type.value,
        }
        for trade in trades
    ]


def format_portfolio(
        current_value: dict, initial_value: dict,
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
        backend_enums.PortfolioKeys.UNIT.value: unit,
        backend_enums.PortfolioKeys.BOT_ID.value: bot_id,
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


def format_bot_config_and_stats(profile_name, profitability, bot_id):
    return {
        backend_enums.ConfigKeys.CURRENT.value: {
            backend_enums.CurrentConfigKeys.PROFILE_NAME.value: profile_name,
            backend_enums.CurrentConfigKeys.PROFITABILITY.value: float(profitability)
        },
        backend_enums.ConfigKeys.BOT_ID.value: bot_id,
    }
