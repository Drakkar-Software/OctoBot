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
    CURRENT_DEPLOYMENT_ID = "current_deployment_id"
    PROFITABILITY = "profitability"
    CURRENT_CONFIG_ID = "current_config_id"
    LAST_TRADE_TIME = "last_trade_time"
    METADATA = "metadata"


class BotDeploymentKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    NAME = "name"
    VERSION = "version"
    BOT_ID = "bot_id"
    CURRENT_HOSTING_ID = "current_hosting_id"
    PRODUCT_ID = "product_id"
    CURRENT_STORAGE_ID = "current_storage_id"
    SUBSCRIPTION_ID = "subscription_id"
    CURRENT_URL_ID = "current_url_id"
    TYPE = "type"


class BotDeploymentURLKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    REGION = "region"
    DEPLOYMENT_ID = "deployment_id"
    URL = "url"


class SignalKeys(enum.Enum):
    ID = "id"
    TIME = "time"
    PRODUCT_ID = "product_id"
    SIGNAL = "signal"


class ProductKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    CONTENT = "content"
    UPDATED_AT = "updated_at"
    SLUG = "slug"
    CURRENT_VERSION_ID = "current_version_id"
    AUTHOR_ID = "author_id"
    LOGO_URL = "logo_url"
    DOWNLOAD_URL = "download_url"
    CATEGORY_ID= "category_id"
    ATTRIBUTES= "attributes"
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
    METADATA = "metadata"


class OrderKeys(enum.Enum):
    # todo use same as TradeKeys ?
    ID = "id"
    ORDER_ID = "order_id"
    EXCHANGE_ORDER_ID = "exchange_order_id"
    BOT_ID = "bot_id"
    EXCHANGE = "exchange"
    SYMBOL = "symbol"
    PRICE = "price"
    TIME = "time"
    TYPE = "type"
    SIDE = "side"
    QUANTITY = "quantity"
    REDUCE_ONLY = "reduce_only"
    TAG = "tag"
    SELF_MANAGED = "self_managed"
    # order metadata
    EXCHANGE_CREATION_PARAMS = "ecp"
    ENTRIES = "e"
    GROUP_ID = "group_id"
    GROUP_TYPE = "group_type"
    CHAINED_ORDERS = "chained_orders"
    UPDATE_WITH_TRIGGERING_ORDER_FEES = "utf"


class PortfolioKeys(enum.Enum):
    ID = "id"
    BOT_ID = "bot_id"
    CURRENT_VALUE = "current_value"
    INITIAL_VALUE = "initial_value"
    PROFITABILITY = "profitability"
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


class BotConfigKeys(enum.Enum):
    ID = "id"
    BOT_ID = "bot_id"
    PRODUCT_CONFIG_ID = "product_config_id"
    EXCHANGES = "exchanges"
    OPTIONS = "options"


class UserKeys(enum.Enum):
    ID = "id"
    EMAIL = "email"
    USER_METADATA = "user_metadata"
    LAST_SIGN_IN_AT = "last_sign_in_at"


class DeploymentTypes(enum.Enum):
    SELF_HOSTED = "self_hosted"
    CLOUD = "cloud"
