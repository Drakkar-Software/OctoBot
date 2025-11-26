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
    POSITIONS = "positions"


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
    STOPPED_AT = "stopped_at"


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
    ARCHIVED = "archived"


class ProductSubscriptionDesiredStatus(enum.Enum):
    ACTIVE = 'active'
    CANCELED = "canceled"


class BotDeploymentErrorsStatuses(enum.Enum):
    NO_ERROR = None
    INTERNAL_SERVER_ERROR = "internal_server_error"
    INVALID_CONFIG = "invalid_config"
    INVALID_EXCHANGE_CREDENTIALS = "invalid_exchange_credentials"
    MISSING_API_KEY_TRADING_RIGHTS = "missing_api_key_trading_rights"
    INCOMPATIBLE_USER_EXCHANGE_ACCOUNT_WITH_CONFIG = "incompatible_user_exchange_account_with_config"
    ALREADY_USED_EXCHANGE_ACCOUNT = "already_used_exchange_account"
    MISSING_MINIMAL_FUNDS = "missing_minimal_funds"
    TOO_MANY_ORDERS_TO_EXECUTE_STRATEGY = "too_many_orders_to_execute_strategy"
    MISSING_CONFIG = "missing_config"
    EXPIRED_BOT = "expired_bot"
    MAX_SIMULATORS_REACHED = "max_simulators_reached"


class ExchangeAccountStatuses(enum.Enum):
    NO_STATUS = None
    PENDING_PORTFOLIO_REFRESH = "pending_portfolio_refresh"
    NO_PENDING_ACTION = "no_pending_action"


class BotLogContentKeys(enum.Enum):
    REASON = "reason"


class BotLogType(enum.Enum):
    # order is important to keep priority on log to emit on a bot wakeup
    INVALID_EXCHANGE_CREDENTIALS = "invalid_exchange_credentials"
    MISSING_API_KEY_TRADING_RIGHTS = "missing_api_key_trading_rights"
    CREATED_ORDERS = "created_orders"
    CANCELLED_ORDERS = "cancelled_orders"
    REBALANCING_DONE = "rebalancing_done"
    REBALANCING_SKIPPED = "rebalancing_skipped"
    USER_DEPOSIT = "user_deposit"
    USER_WITHDRAW = "user_withdraw"
    IMPORTANT_GAIN = "important_gain"
    IMPORTANT_LOSS = "important_loss"
    OPENED_POSITION = "opened_position"
    CLOSED_POSITION = "closed_position"
    UNSUPPORTED_HEDGE_POSITION = "unsupported_hedge_position"
    NOTHING_TO_DO = "nothing_to_do"
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_RESTARTED = "bot_restarted"
    MISSING_MINIMAL_FUNDS = "missing_minimal_funds"
    CHANGED_PRODUCT = "changed_product"
    IMPOSSIBLE_TO_CREATE_ALL_REQUIRED_ORDERS = "impossible_to_create_all_required_orders"
    RESUMED_STRATEGY_EXECUTION = "resumed_strategy_execution"
    STOPPED_STRATEGY_EXECUTION = "stopped_strategy_execution"
    RESIZED_SUB_PORTFOLIO = "resized_sub_portfolio"
    NO_LOG = None


class ExchangeKeys(enum.Enum):
    ID = "id"
    INTERNAL_NAME = "internal_name"
    EXCHANGE_CREDENTIAL_ID = "exchange_credential_id"
    EXCHANGE_ID = "exchange_id"
    EXCHANGE_TYPE = "exchange_type"
    SANDBOXED = "sandboxed"
    AVAILABILITY = "availability"
    URL = "url"
    TRUSTED_IPS = "trusted_ips"


class ExchangeSupportValues(enum.Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class ExchangeAvailabilities(enum.Enum):
    SPOT = "spot"
    FUTURES = "futures"
    OPEN_SOURCE = "open_source"
    MARKET_MAKING = "market_making"


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
    FILLED = "filled"
    EXCHANGE_ID = "exchange_id"
    SYMBOL = "symbol"
    TYPE = "type"
    CHAINED = "chained"
    SIDE = "side"
    TRIGGER_ABOVE = "trigger_above"
    REDUCE_ONLY = "reduce_only"
    IS_ACTIVE = "is_active"


class PositionKeys(enum.Enum):
    EXCHANGE = "exchange"
    TIME = "time"
    POSITION_ID = "position_id"
    # subset of octobot_trading.enums.ExchangeConstantsPositionColumns
    SYMBOL = "symbol"
    LOCAL_ID = "local_id"
    ENTRY_PRICE = "entry_price"
    MARK_PRICE = "mark_price"
    LIQUIDATION_PRICE = "liquidation_price"
    UNREALIZED_PNL = "unrealised_pnl"
    REALISED_PNL = "realised_pnl"
    QUANTITY = "quantity"
    SIZE = "size"
    NOTIONAL = "notional"
    INITIAL_MARGIN = "initial_margin"
    AUTO_DEPOSIT_MARGIN = "auto_deposit_margin"
    COLLATERAL = "collateral"
    LEVERAGE = "leverage"
    MARGIN_TYPE = "margin_type"
    POSITION_MODE = "position_mode"
    MAINTENANCE_MARGIN_RATE = "maintenance_margin_rate"
    STATUS = "status"
    SIDE = "side"


class PortfolioKeys(enum.Enum):
    ID = "id"
    BOT_ID = "bot_id"
    CURRENT_VALUE = "current_value"
    INITIAL_VALUE = "initial_value"
    PROFITABILITY = "profitability"
    UNIT = "unit"
    CONTENT = "content"
    PORTFOLIO_TYPE = "portfolio_type"
    LOCKED_ASSETS = "locked_assets"


class PortfolioTypes(enum.Enum):
    FULL_PORTFOLIO = "full-portfolio"
    SUB_PORTFOLIO = "sub-portfolio"


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
    EXCHANGE_ACCOUNT_ID = "exchange_account_id"
    OPTIONS = "options"
    IS_SIMULATED = "is_simulated"
    CREATED_AT = "created_at"


class NestedProductConfigKeys(enum.Enum):
    NESTED_CONFIG_ROOT = "nested_config"
    SLUG = "slug"


class BotConfigOptionsKeys(enum.Enum):
    TENTACLES = "tentacles"
    NESTED_CONFIG = NestedProductConfigKeys.NESTED_CONFIG_ROOT.value


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
