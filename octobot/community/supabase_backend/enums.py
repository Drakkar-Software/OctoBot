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
    CREATED_AT = "created_at"
    NAME = "name"
    USER_ID = "user_id"
    CURRENT_PORTFOLIO_ID = "current_portfolio_id"
    CURRENT_DEPLOYMENT_ID = "current_deployment_id"
    CURRENT_CONFIG_ID = "current_config_id"
    LAST_TRADE_TIME = "last_trade_time"
    METADATA = "metadata"
    ORDERS = "orders"


class ProductsSubscriptionsKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    STATUS = "status"
    DESIRED_STATUS = "desired_status"


class BotDeploymentKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    NAME = "name"
    VERSION = "version"
    BOT_ID = "bot_id"
    CURRENT_HOSTING_ID = "current_hosting_id"
    PRODUCT_ID = "product_id"
    CURRENT_STORAGE_ID = "current_storage_id"
    SUBSCRIPTION_ID = "product_subscription_id"
    CURRENT_URL_ID = "current_url_id"
    STATUS = "status"
    DESIRED_STATUS = "desired_status"
    TYPE = "type"
    METADATA = "metadata"
    ERROR_STATUS = "error_status"
    ACTIVITIES = "activities"
    EXPIRATION_TIME = "expiration_time"


class BotDeploymentActivitiesKeys(enum.Enum):
    LAST_ACTIVITY = "last_activity"
    NEXT_ACTIVITY = "next_activity"


class BotDeploymentURLKeys(enum.Enum):
    ID = "id"
    CREATED_AT = "created_at"
    REGION = "region"
    DEPLOYMENT_ID = "deployment_id"
    URL = "url"


class BotDeploymentStatus(enum.Enum):
    CREATED = 'created'
    UPDATED = "updated"
    RUNNING = "running"
    STOPPED = "stopped"
    PENDING = "pending"
    UNKNOWN = "unknown"


class ProductSubscriptionDesiredStatus(enum.Enum):
    ACTIVE = 'active'
    CANCELED = "canceled"


class BotDeploymentErrorsStatuses(enum.Enum):
    NO_ERROR = None
    INTERNAL_SERVER_ERROR = "internal_server_error"
    INVALID_CONFIG = "invalid_config"
    INVALID_EXCHANGE_CREDENTIALS = "invalid_exchange_credentials"
    INCOMPATIBLE_USER_EXCHANGE_ACCOUNT_WITH_CONFIG = "incompatible_user_exchange_account_with_config"
    ALREADY_USED_EXCHANGE_ACCOUNT = "already_used_exchange_account"
    MISSING_MINIMAL_FUNDS = "missing_minimal_funds"
    MISSING_CONFIG = "missing_config"
    EXPIRED_BOT = "expired_bot"
    MAX_SIMULATORS_REACHED = "max_simulators_reached"


class ExchangeAccountStatuses(enum.Enum):
    NO_STATUS = None
    PENDING_PORTFOLIO_REFRESH = "pending_portfolio_refresh"
    NO_PENDING_ACTION = "no_pending_action"


class ExchangeKeys(enum.Enum):
    ID = "id"
    INTERNAL_NAME = "internal_name"


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
    CURRENT_CONFIG_ID = "current_config_id"
    AUTHOR_ID = "author_id"
    LOGO_URL = "logo_url"
    DOWNLOAD_URL = "download_url"
    CATEGORY_ID = "category_id"
    ATTRIBUTES = "attributes"
    METADATA = "metadata"
    PARENT_ID = "parent_id"
    VISIBILITY = "visibility"
    CURRENT_RESULT_ID = "current_result_id"


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
    VOLUME = "volume"
    BROKER_APPLIED = "broker_applied"
    METADATA = "metadata"


class OrderKeys(enum.Enum):
    TIME = "time"
    EXCHANGE = "exchange"
    PRICE = "price"
    QUANTITY = "quantity"
    EXCHANGE_ID = "exchange_id"
    SYMBOL = "symbol"
    TYPE = "type"
    CHAINED = "chained"


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
    SIMULATED = "simulated"


class ProfileConfigKeys(enum.Enum):
    ID = "id"
    PRODUCT_CONFIG_ID = "product_id"
    VERSION = "version"
    CONFIG = "config"


class UserKeys(enum.Enum):
    ID = "id"
    EMAIL = "email"
    USER_METADATA = "user_metadata"
    LAST_SIGN_IN_AT = "last_sign_in_at"


class DeploymentTypes(enum.Enum):
    SELF_HOSTED = "self_hosted"
    CLOUD = "cloud"


class SQLValues(enum.Enum):
    NULL = "null"
