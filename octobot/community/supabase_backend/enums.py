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

import enum


class BotKeys(enum.Enum):
    ID = "id"
    NAME = "name"
    USER_ID = "user_id"
    CURRENT_PORTFOLIO_ID = "current_portfolio_id"
    DEPLOYMENT_ID = "deployment_id"
    PROFITABILITY = "profitability"
    CURRENT_CONFIG_ID = "current_config_id"
    LAST_TRADE_TIME = "last_trade_time"
    METADATA = "metadata"


class TradeKeys(enum.Enum):
    ID = "id"
    TRADE_ID = "trade_id"
    BOT_ID = "bot_id"
    TIME = "time"
    EXCHANGE = "exchange"
    PRICE = "price"
    QUANTITY = "quantity"
    SYMBOL = "symbol"
    TYPE = "type"


class PortfolioKeys(enum.Enum):
    ID = "id"
    BOT_ID = "bot_id"
    CURRENT_VALUE = "current_value"
    INITIAL_VALUE = "initial_value"
    UNIT = "unit"
    CONTENT = "content"


class PortfolioHistoryKeys(enum.Enum):
    TIME = "time"
    PORTFOLIO_ID = "portfolio_id"
    VALUE = "value"


class PortfolioAssetKeys(enum.Enum):
    ASSET = "asset"
    VALUE = "value"
    QUANTITY = "quantity"


class ConfigKeys(enum.Enum):
    ID = "id"
    BOT_ID = "bot_id"
    CREATED_AT = "created_at"
    CURRENT = "current"


class CurrentConfigKeys(enum.Enum):
    PROFILE_NAME = "profile_name"
    PROFITABILITY = "profitability"
