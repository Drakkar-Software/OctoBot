#  Drakkar-Software OctoBot-Commons
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
import os
import octobot_commons.enums as enums


def parse_boolean_environment_var(env_key: str, default_value: str) -> bool:
    """
    :param env_key: the environment var key
    :param default_value: the default value
    :return: True when the var value is "True" or "true" else false
    """
    return bool(os.getenv(env_key, default_value).lower() == "true")


# time
MSECONDS_TO_SECONDS = 1000
MINUTE_TO_SECONDS = 60
MSECONDS_TO_MINUTE = MSECONDS_TO_SECONDS * MINUTE_TO_SECONDS
HOURS_TO_SECONDS = MINUTE_TO_SECONDS * 60
HOURS_TO_MSECONDS = MSECONDS_TO_SECONDS * MINUTE_TO_SECONDS * MINUTE_TO_SECONDS
DAYS_TO_SECONDS = HOURS_TO_SECONDS * 24

# Strings
CONFIG_WILDCARD = "*"
CONFIG_SYMBOLS_WILDCARD = ["*"]
PORTFOLIO_AVAILABLE = "available"
MARGIN_PORTFOLIO = "margin"
PORTFOLIO_TOTAL = "total"

# config
CONFIG_ENABLED_OPTION = "enabled"
CONFIG_DEBUG_OPTION = "DEV-MODE"
CONFIG_TIME_FRAME = "time_frame"
USER_FOLDER = "user"
CONFIG_FOLDER = "config"
CONFIG_FILE = "config.json"
SAFE_DUMP_SUFFIX = ".back"
DEFAULT_CONFIG_FILE = "default_config.json"
DEFAULT_CONFIG_FILE_PATH = f"{CONFIG_FOLDER}/{DEFAULT_CONFIG_FILE}"
SCHEMA = "schema"
CONFIG_FILE_EXT = ".json"
CONFIG_FILE_SCHEMA = f"{CONFIG_FOLDER}/config_{SCHEMA}.json"
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_SAVED_HISTORICAL_TIMEFRAMES = "saved_historical_timeframes"
CONFIG_OPTIMIZER_ID = "optimizer_id"
CONFIG_BACKTESTING_ID = "backtesting_id"
CONFIG_CURRENT_LIVE_ID = "current-live-id"
DEFAULT_CURRENT_LIVE_ID = 1

# profiles
PROFILES_FOLDER = "profiles"
USER_PROFILES_FOLDER = f"{USER_FOLDER}/{PROFILES_FOLDER}"
PROFILE_CONFIG_FILE = "profile.json"
CONFIG_PROFILE = "profile"
CONFIG_BACKTESTING_PROFILE = "backtesting_profile"
DEFAULT_PROFILE = "default"
DEFAULT_PROFILE_FILE = f"{CONFIG_PROFILE}.json"
CONFIG_NAME = "name"
CONFIG_SLUG = "slug"
CONFIG_DESCRIPTION = "description"
CONFIG_AVATAR = "avatar"
CONFIG_ORIGIN_URL = "origin_url"
CONFIG_AUTO_UPDATE = "auto_update"
CONFIG_READ_ONLY = "read_only"
CONFIG_IMPORTED = "imported"
CONFIG_EXTRA_BACKTESTING_TIME_FRAMES = "extra_backtesting_time_frames"
CONFIG_COMPLEXITY = "complexity"
CONFIG_RISK = "risk"
CONFIG_TYPE = "type"
PROFILE_CONFIG = "config"
CONFIG_ID = "id"
PROFILE_FILE_SCHEMA = f"{CONFIG_FOLDER}/profile_{SCHEMA}.json"
PROFILE_EXPORT_FORMAT = "zip"
IMPORTED_PROFILE_PREFIX = "imported"
USE_CURRENT_PROFILE = "use_current_profile"
PROFILE_REFRESH_HOURS_INTERVAL = int(os.getenv("PROFILE_REFRESH_HOURS_INTERVAL", "24"))

# Config currencies
CONFIG_CRYPTO_CURRENCIES = "crypto-currencies"
CONFIG_CRYPTO_CURRENCY = "crypto-currency"
CONFIG_CRYPTO_PAIRS = "pairs"
CONFIG_CRYPTO_QUOTE = "quote"
CONFIG_CRYPTO_ADD = "add"
TRADING_SYMBOL_REGEX = "([a-zA-Z]|\\d){1,}\\/([a-zA-Z]|\\d){1,}"

# Exchange
CONFIG_EXCHANGES = "exchanges"
CONFIG_EXCHANGE_KEY = "api-key"
CONFIG_EXCHANGE_SECRET = "api-secret"
CONFIG_EXCHANGE_PASSWORD = "api-password"
CONFIG_EXCHANGE_UID = "api-uid"
CONFIG_EXCHANGE_ACCESS_TOKEN = "access_token"
CONFIG_EXCHANGE_TYPE = "exchange-type"
CONFIG_FORCE_AUTHENTICATION = "force-authentication"
CONFIG_CONTRACT_TYPE = "contract-type"
CONFIG_REQUIRED_EXTRA_TIMEFRAMES = "required_extra_timeframes"
CONFIG_EXCHANGE_SANDBOXED = "sandboxed"
CONFIG_EXCHANGE_FUTURE = "future"
CONFIG_EXCHANGE_MARGIN = "margin"
CONFIG_EXCHANGE_OPTION = "option"
CONFIG_EXCHANGE_SPOT = "spot"
CONFIG_EXCHANGE_REST_ONLY = "rest_only"
CONFIG_EXCHANGE_WEB_SOCKET = "web-socket"
CONFIG_EXCHANGE_SUB_ACCOUNT = "sub_account"
CONFIG_EXCHANGE_ENCRYPTED_VALUES = [
    CONFIG_EXCHANGE_KEY,
    CONFIG_EXCHANGE_SECRET,
    CONFIG_EXCHANGE_PASSWORD,
]

# Trader
CONFIG_TRADING = "trading"
CONFIG_TRADER = "trader"
CONFIG_LOAD_TRADE_HISTORY = "load-trade-history"
CONFIG_TRADER_RISK = "risk"
CONFIG_TRADER_PAUSED = "paused"
CONFIG_TRADER_ALLOW_ARTIFICIAL_ORDERS = "allow-artificial-orders"
CONFIG_TRADER_RISK_MIN = 0.05
CONFIG_TRADER_RISK_MAX = 1
CONFIG_TRADER_REFERENCE_MARKET = "reference-market"
DEFAULT_STORAGE_TRADING_MODE = "default"

# Simulator
CONFIG_SIMULATOR = "trader-simulator"
CONFIG_STARTING_PORTFOLIO = "starting-portfolio"
SIMULATOR_CURRENT_PORTFOLIO = "simulator_current_portfolio"
CONFIG_SIMULATOR_FEES = "fees"
CONFIG_SIMULATOR_FEES_MAKER = "maker"
CONFIG_SIMULATOR_FEES_TAKER = "taker"
CONFIG_SIMULATOR_FEES_WITHDRAW = "withdraw"

# Optimization campaigns
DEFAULT_CAMPAIGN = "default_campaign"

# Optimizer
OPTIMIZER_RUNS_FOLDER = "optimizer"

# OS
PLATFORM_DATA_SEPARATOR = ":"
CLOCK_REFRESH_HOURS_INTERVAL = int(os.getenv("CLOCK_REFRESH_HOURS_INTERVAL", "4"))
RESOURCES_WATCHER_MINUTES_INTERVAL = float(
    os.getenv("RESOURCES_WATCHER_MINUTES_INTERVAL", "10")
)
BYTES_BY_GB = 1000000000

# Evaluators
MIN_EVAL_TIME_FRAME = enums.TimeFrames.ONE_MINUTE
INIT_EVAL_NOTE = 0
START_PENDING_EVAL_NOTE = "0"

# tentacles
TENTACLE_DEFAULT_CONFIG = "default_config"
CONFIG_TENTACLES_FILE = "tentacles_config.json"
EVALUATOR_PRIORITY = "priority"
DEFAULT_EVALUATOR_PRIORITY = 0
CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT = "required_candles_count"
CONFIG_HISTORICAL_CONFIGURATION = "_historical_configuration"
NESTED_TENTACLE_CONFIG = "nested_tentacle_configuration"
CONFIG_ACTIVATION_TOPICS = "activation method"
CONFIG_TRIGGER_TIMEFRAMES = "Trigger_timeframes"
CONFIG_EMIT_TRADING_SIGNALS = "emit_trading_signals"
CONFIG_TRADING_SIGNALS_STRATEGY = "trading_strategy"
ALLOW_DEFAULT_CONFIG = "allow_default_config"

# terms of service
CONFIG_ACCEPTED_TERMS = "accepted_terms"

# distribution
DEFAULT_DISTRIBUTION = "default"
CONFIG_DISTRIBUTION = "distribution"

# metrics
CONFIG_METRICS = "metrics"
CONFIG_METRICS_BOT_ID = "metrics-bot-id"
TIMER_BEFORE_METRICS_REGISTRATION_SECONDS = 600
TIMER_BETWEEN_METRICS_UPTIME_UPDATE = float(
    os.getenv("TIMER_BETWEEN_METRICS_UPTIME_UPDATE", str(3600 * 4))
)
METRICS_URL = os.getenv("METRICS_OCTOBOT_ONLINE_URL", "https://metrics.octobot.online/")
METRICS_ROUTE_GEN_BOT_ID = "gen-bot-id"
METRICS_ROUTE = "metrics"
METRICS_ROUTE_COMMUNITY = f"{METRICS_ROUTE}/community"
METRICS_ROUTE_UPTIME = f"{METRICS_ROUTE}/uptime"
METRICS_ROUTE_REGISTER = f"{METRICS_ROUTE}/register"
COMMUNITY_TOPS_COUNT = 1000

# default values in config files and interfaces
DEFAULT_API_KEY = "your-api-key-here"
DEFAULT_API_SECRET = "your-api-secret-here"
DEFAULT_API_PASSWORD = "your-api-password-here"
DEFAULT_EXCHANGE_TYPE = CONFIG_EXCHANGE_SPOT
NO_KEY_VALUE = "NO KEY"
DEFAULT_CONFIG_VALUES = {
    DEFAULT_API_KEY,
    DEFAULT_API_SECRET,
    DEFAULT_API_PASSWORD,
    "NOKEY",
    NO_KEY_VALUE,
    "Empty",
}

# cache
CACHE_FOLDER = "cache"
CACHE_FILE = "cache.json"
CACHE_HASH_SIZE = 15
CACHE_RELATED_DATA_SEPARATOR = "##"
LOCAL_BOT_DATA = "local_bot_data"
DO_NOT_CACHE = "do_not_cache"
DO_NOT_OVERRIDE_CACHE = "do_not_override_cache"
DEFAULT_IGNORED_VALUE = -1
UNPROVIDED_CACHE_IDENTIFIER = "_unprovided"

# Async settings
DEFAULT_FUTURE_TIMEOUT = 120

# Github urls
GITHUB_RAW_CONTENT_URL = "https://raw.githubusercontent.com"
GITHUB_API_CONTENT_URL = "https://api.github.com"
GITHUB_BASE_URL = "https://github.com"
GITHUB_ORGANISATION = "Drakkar-Software"

# External resources
EXTERNAL_RESOURCE_URL = "https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/external_resources.json"

# Run databases
DATA_FOLDER = "data"
DB_SEPARATOR = "_"
TINYDB_EXT = ".json"
MAX_BACKTESTING_RUNS = 500000
MAX_OPTIMIZER_RUNS = 50000
FORCE_BACKTESTING_LOGS = parse_boolean_environment_var(
    "FORCE_BACKTESTING_LOGS", "false"
)

# DSL interpreter
BASE_OPERATORS_LIBRARY = "base"
CONTEXTUAL_OPERATORS_LIBRARY = "contextual"

# Logging
EXCEPTION_DESC = "exception_desc"
IS_EXCEPTION_DESC = "is_exception_desc"

# from https://www.coingecko.com/en/categories/stablecoins
USD_LIKE_COINS = [
    "USDT",
    "USDC",
    "TUSD",
    "USDE",
    "USDS",
    "BUSD",
    "DAI",
    "USD",
    "USDD",
    "USDP",
    "GUSD",
    "LUSD",
    "FDUSD",
]
DEFAULT_REFERENCE_MARKET = "USDT"
USUAL_REFERENCE_MARKET_USD_LIKE_COINS = [
    DEFAULT_REFERENCE_MARKET,
    "USDC",
]

# from coinbase and binance fiat pairs
FIAT_NON_USD_LIKE_COINS = [
    "EUR",
    "GBP",
    "TRY",
    "BRL",
    "ARS",
]

USD_LIKE_AND_FIAT_COINS = USD_LIKE_COINS + FIAT_NON_USD_LIKE_COINS

ENABLE_CERTIFI_SSL_CERTIFICATES = parse_boolean_environment_var(
    "ENABLE_CERTIFI_SSL_CERTIFICATES", "true"
)
KNOWN_POTENTIALLY_SSL_FAILED_REQUIRED_URL = (
    "https://tentacles.octobot.online/officials/packages/full/base/1.0.9/metadata.yaml"
)
IS_DEV_MODE_ENABLED = parse_boolean_environment_var(CONFIG_DEBUG_OPTION, "False")
USE_MINIMAL_LIBS = parse_boolean_environment_var("USE_MINIMAL_LIBS", "false")
