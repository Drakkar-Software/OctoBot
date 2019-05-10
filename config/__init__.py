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

from logging import WARNING
from enum import Enum
from typing import NewType, Any, Dict

PROJECT_NAME = "OctoBot"
SHORT_VERSION = "0.3.4"  # major.minor.revision
PATCH_VERSION = ""  # patch : pX
VERSION_DEV_PHASE = ""  # alpha : a / beta : b / release candidate : rc
VERSION_PHASE = ""  # XX
VERSION = f"{SHORT_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"
LONG_VERSION = f"{SHORT_VERSION}{PATCH_VERSION}{VERSION_DEV_PHASE}{VERSION_PHASE}"

# logs
LOG_DATABASE = "log_db"
LOG_NEW_ERRORS_COUNT = "log_new_errors_count"
BACKTESTING_NEW_ERRORS_COUNT = "log_backtesting_errors_count"
STORED_LOG_MIN_LEVEL = WARNING
LOGS_FOLDER = "logs"

# github
GITHUB = "github"
GITHUB_RAW_CONTENT_URL = "https://raw.githubusercontent.com"
GITHUB_API_CONTENT_URL = "https://api.github.com"
GITHUB_BASE_URL = "https://github.com"
GITHUB_ORGANISATION = "Drakkar-Software"
GITHUB_REPOSITORY = f"{GITHUB_ORGANISATION}/{PROJECT_NAME}"
GITHUB_URL = f"{GITHUB_BASE_URL}/{GITHUB_REPOSITORY}"
ASSETS_BRANCH = "assets"
OCTOBOT_BACKGROUND_IMAGE = "static/img/octobot.png"
OCTOBOT_ICON = "static/favicon.ico"
EXTERNAL_RESOURCES_FILE = "external_resources.json"
EXTERNAL_RESOURCE_CURRENT_USER_FORM = "current-user-feedback-form"
EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS = "public-announcements"

# git
GIT_ORIGIN = "origin"
ORIGIN_URL = f"{GITHUB_URL}.git"

# terms of service
CONFIG_ACCEPTED_TERMS = "accepted_terms"

# constants
MSECONDS_TO_SECONDS = 1000
MINUTE_TO_SECONDS = 60
HOURS_TO_SECONDS = MINUTE_TO_SECONDS * 60
HOURS_TO_MSECONDS = MSECONDS_TO_SECONDS * MINUTE_TO_SECONDS * MINUTE_TO_SECONDS
DAYS_TO_SECONDS = HOURS_TO_SECONDS * 24

CONFIG_GLOBAL_UTILS = "global_utils"
CONFIG_ENABLED_OPTION = "enabled"
CONFIG_SYMBOL = "symbol"
CONFIG_WILDCARD = "*"
CONFIG_SAVE_EVALUATION = "SAVE_EVALUATIONS"
EVALUATION_SAVING_FILE_ENDING = "_evaluations.csv"
EVALUATION_SAVING_COLUMN_SEPARATOR = ";"
EVALUATION_SAVING_ROW_SEPARATOR = "\n"

BOT_TOOLS_BACKTESTING = "backtesting"
BOT_TOOLS_STRATEGY_OPTIMIZER = "strategy_optimizer"
BOT_TOOLS_RECORDER = "recorder"

# metrics
CONFIG_METRICS = "metrics"
CONFIG_METRICS_BOT_ID = "metrics-bot-id"
TIMER_BEFORE_METRICS_REGISTRATION_SECONDS = 600
TIMER_BETWEEN_METRICS_UPTIME_UPDATE = 3600 * 4
METRICS_URL = "https://octobotmetrics.herokuapp.com/"
METRICS_ROUTE_GEN_BOT_ID = "gen-bot-id"
METRICS_ROUTE = "metrics"
METRICS_ROUTE_COMMUNITY = f"{METRICS_ROUTE}/community"
METRICS_ROUTE_UPTIME = f"{METRICS_ROUTE}/uptime"
METRICS_ROUTE_REGISTER = f"{METRICS_ROUTE}/register"
COMMUNITY_TOPS_COUNT = 1000
PLATFORM_DATA_SEPARATOR = ":"

# default values in config files and interfaces
DEFAULT_CONFIG_VALUES = {"your-api-key-here", "your-api-secret-here", "your-api-password-here", "NOKEY", "Empty"}

# Async settings
DEFAULT_FUTURE_TIMEOUT = 120

# Advanced
CONFIG_ADVANCED_CLASSES = "advanced_classes"
CONFIG_ADVANCED_INSTANCES = "advanced_instances"

# Backtesting
CONFIG_BACKTESTING = "backtesting"
CONFIG_ANALYSIS_ENABLED_OPTION = "post_analysis_enabled"
CONFIG_BACKTESTING_DATA_FILES = "files"
CONFIG_BACKTESTING_OTHER_MARKETS_STARTING_PORTFOLIO = 10000
BACKTESTING_DATA_OHLCV = "ohlcv"
BACKTESTING_DATA_TRADES = "trades"

# Data collector
CONFIG_DATA_COLLECTOR = "data_collector"
CONFIG_DATA_COLLECTOR_ZIPLINE = "zipline"
DATA_COLLECTOR_REFRESHER_TIME = MINUTE_TO_SECONDS
CONFIG_DATA_COLLECTOR_PATH = "backtesting/collector/data/"

# Trading
CONFIG_EXCHANGES = "exchanges"
CONFIG_EXCHANGE_KEY = "api-key"
CONFIG_EXCHANGE_SECRET = "api-secret"
CONFIG_EXCHANGE_PASSWORD = "api-password"
CONFIG_EXCHANGE_WEB_SOCKET = "web-socket"
DEFAULT_REST_RETRY_COUNT = 3
CONFIG_TRADING = "trading"
CONFIG_TRADING_TENTACLES = "trading-tentacles"
CONFIG_TRADER = "trader"
CONFIG_SIMULATOR = "trader-simulator"
CONFIG_STARTING_PORTFOLIO = "starting-portfolio"
CONFIG_TRADER_RISK = "risk"
CONFIG_TRADER_RISK_MIN = 0.05
CONFIG_TRADER_RISK_MAX = 1
ORDER_REFRESHER_TIME = 15
ORDER_REFRESHER_TIME_WS = 1
UPDATER_MAX_SLEEPING_TIME = 2
SIMULATOR_LAST_PRICES_TO_CHECK = 50
ORDER_CREATION_LAST_TRADES_TO_USE = 10
CONFIG_TRADER_REFERENCE_MARKET = "reference-market"
DEFAULT_REFERENCE_MARKET = "BTC"
MARKET_SEPARATOR = "/"
CURRENCY_DEFAULT_MAX_PRICE_DIGITS = 8
EXCHANGE_ERROR_SLEEPING_TIME = 10
CONFIG_EXCHANGE_ENCRYPTED_VALUES = [CONFIG_EXCHANGE_KEY, CONFIG_EXCHANGE_SECRET, CONFIG_EXCHANGE_PASSWORD]

# Trader persistence
HISTORY_EXCHANGE_KEY = "exchange"
SIMULATOR_INITIAL_STARTUP_PORTFOLIO = "simulator_initial_portfolio"
REAL_INITIAL_STARTUP_PORTFOLIO = "real_initial_portfolio"
SIMULATOR_CURRENT_PORTFOLIO = "simulator_current_portfolio"
SIMULATOR_INITIAL_STARTUP_PORTFOLIO_VALUE = "simulator_initial_portfolio_value"
REAL_INITIAL_STARTUP_PORTFOLIO_VALUE = "real_initial_portfolio_value"
WATCHED_MARKETS_INITIAL_STARTUP_VALUES = "initial_watched_markets_value"
REFERENCE_MARKET = "reference_market"
CURRENT_PORTFOLIO_STRING = "Current Portfolio :"
CONFIG_ENABLED_PERSISTENCE = "multi-session-profitability"


# Exchanges
TESTED_EXCHANGES = ["binance", "coinbasepro", "kucoin2"]
SIMULATOR_TESTED_EXCHANGES = ["bitfinex", "bittrex", "coinbasepro", "kraken", "kucoin2", "poloniex", "cryptopia",
                              "bitmex"]

CONFIG_SIMULATOR_FEES = "fees"
CONFIG_SIMULATOR_FEES_MAKER = "maker"
CONFIG_SIMULATOR_FEES_TAKER = "taker"
CONFIG_SIMULATOR_FEES_WITHDRAW = "withdraw"
CONFIG_DEFAULT_FEES = 0.1
CONFIG_DEFAULT_SIMULATOR_FEES = 0

CONFIG_PORTFOLIO_INFO = "info"
CONFIG_PORTFOLIO_FREE = "free"
CONFIG_PORTFOLIO_USED = "used"
CONFIG_PORTFOLIO_TOTAL = "total"

# Notification
CONFIG_NOTIFICATION_TYPE = "notification-type"
CONFIG_NOTIFICATION_INSTANCE = "notifier"
CONFIG_CATEGORY_NOTIFICATION = "notification"
PROJECT_NOTIFICATION = f"{PROJECT_NAME} {CONFIG_CATEGORY_NOTIFICATION}"
CONFIG_NOTIFICATION_GLOBAL_INFO = "global-info"
CONFIG_NOTIFICATION_PRICE_ALERTS = "price-alerts"
CONFIG_NOTIFICATION_TRADES = "trades"
NOTIFICATION_STARTING_MESSAGE = f"OctoBot v{LONG_VERSION} starting..."
NOTIFICATION_STOPPING_MESSAGE = f"OctoBot v{LONG_VERSION} stopping..."
REAL_TRADER_STR = "[Real Trader] "
SIMULATOR_TRADER_STR = "[Simulator] "
PAID_FEES_STR = "Paid fees"
DICT_BULLET_TOKEN_STR = "\n "

# DEBUG options
CONFIG_DEBUG_OPTION_PERF = "performance-analyser"
CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN = 5
CONFIG_DEBUG_OPTION = "DEV-MODE"
FORCE_ASYNCIO_DEBUG_OPTION = False

# SERVICES
CONFIG_CATEGORY_SERVICES = "services"
CONFIG_SERVICE_INSTANCE = "service_instance"

# telegram
CONFIG_TELEGRAM = "telegram"
CONFIG_TOKEN = "token"
CONFIG_TELEGRAM_CHANNEL = "telegram-channels"
MESSAGE_PARSE_MODE = 'parse_mode'
CONFIG_TELEGRAM_ALL_CHANNEL = "*"
CONFIG_GROUP_MESSAGE = "group-message"
CONFIG_GROUP_MESSAGE_DESCRIPTION = "group-message-description"

# web
CONFIG_WEB = "web"
CONFIG_WEB_IP = "ip"
CONFIG_WEB_PORT = "port"
DEFAULT_SERVER_IP = '0.0.0.0'
DEFAULT_SERVER_PORT = 5001

# twitter
CONFIG_TWITTERS_ACCOUNTS = "accounts"
CONFIG_TWITTERS_HASHTAGS = "hashtags"
CONFIG_TWITTER = "twitter"
CONFIG_TWITTER_API_INSTANCE = "twitter_api_instance"
CONFIG_TWEET = "tweet"
CONFIG_TWEET_DESCRIPTION = "tweet_description"

# reddit
CONFIG_REDDIT = "reddit"
CONFIG_REDDIT_SUBREDDITS = "subreddits"
CONFIG_REDDIT_ENTRY = "entry"
CONFIG_REDDIT_ENTRY_WEIGHT = "entry_weight"

# Evaluator
CONFIG_EVALUATOR = "evaluator"
CONFIG_FORCED_EVALUATOR = "forced_evaluator"
CONFIG_EVALUATOR_SOCIAL = "Social"
CONFIG_EVALUATOR_REALTIME = "RealTime"
CONFIG_EVALUATOR_TA = "TA"
CONFIG_EVALUATOR_STRATEGIES = "Strategies"
START_PENDING_EVAL_NOTE = "0"  # force exception
INIT_EVAL_NOTE = 0
START_EVAL_PERTINENCE = 1
MAX_TA_EVAL_TIME_SECONDS = 0.1
DEFAULT_WEBSOCKET_REAL_TIME_EVALUATOR_REFRESH_RATE_SECONDS = 1
DEFAULT_REST_REAL_TIME_EVALUATOR_REFRESH_RATE_SECONDS = 60
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_TIME_FRAME = "time_frame"
CONFIG_FORCED_TIME_FRAME = "forced_time_frame"
CONFIG_FILE_EXT = ".json"
CONFIG_CRYPTO_CURRENCIES = "crypto-currencies"
CONFIG_CRYPTO_CURRENCY = "crypto-currency"
CONFIG_CRYPTO_PAIRS = "pairs"
CONFIG_CRYPTO_QUOTE = "quote"
CONFIG_CRYPTO_ADD = "add"
CONFIG_EVALUATORS_WILDCARD = [CONFIG_WILDCARD]
EVALUATOR_ACTIVATION = "activation"
EVALUATOR_EVAL_DEFAULT_TYPE = float

# Socials
SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE = 1

# Stats
STATS_EVALUATOR_HISTORY_TIME = "relevant_history_months"
STATS_EVALUATOR_MAX_HISTORY_TIME = 3

# Tools
DIVERGENCE_USED_VALUE = 30
TOOLS_PATH = "tools"

# Interfaces
CONFIG_INTERFACES = "interfaces"
CONFIG_INTERFACES_WEB = "web"
CONFIG_INTERFACES_TELEGRAM = "telegram"
CONFIG_USERNAMES_WHITELIST = "usernames-whitelist"

# Tentacles (packages)
PYTHON_INIT_FILE = "__init__.py"
TENTACLES_PATH = "tentacles"
TENTACLES_EVALUATOR_PATH = "Evaluator"
TENTACLES_TRADING_PATH = "Trading"
CONFIG_TENTACLES_KEY = "tentacles-packages"
TENTACLE_PACKAGE_DESCRIPTION = "package_description"
TENTACLE_CONFIG_FOLDER = "config"
TENTACLES_TRADING_MODE_PATH = "Mode"
TENTACLES_DEFAULT_BRANCH = SHORT_VERSION
TENTACLES_FORCE_CONFIRM_PARAM = "force"

# Files
CONFIG_FILE = "config.json"
TEMP_RESTORE_CONFIG_FILE = "temp_config.json"
CONFIG_EVALUATOR_FILE = "evaluator_config.json"
CONFIG_TRADING_FILE = "trading_config.json"
CONFIG_EVALUATOR_FILE_PATH = f"{TENTACLES_PATH}/{TENTACLES_EVALUATOR_PATH}/{CONFIG_EVALUATOR_FILE}"
CONFIG_TRADING_FILE_PATH = f"{TENTACLES_PATH}/{TENTACLES_TRADING_PATH}/{CONFIG_TRADING_FILE}"
CONFIG_FOLDER = "config"
CONFIG_DEFAULT_EVALUATOR_FILE = f"{CONFIG_FOLDER}/default_evaluator_config.json"
CONFIG_DEFAULT_TRADING_FILE = f"{CONFIG_FOLDER}/default_trading_config.json"
SCHEMA = "schema"
CONFIG_FILE_SCHEMA = f"{CONFIG_FOLDER}/config_{SCHEMA}.json"
DEFAULT_CONFIG_FILE = f"{CONFIG_FOLDER}/default_config.json"
LOGGING_CONFIG_FILE = f"{CONFIG_FOLDER}/logging_config.ini"
LOG_FILE = f"{LOGS_FOLDER}/{PROJECT_NAME}.log"
STATES_FOLDER = f"{LOGS_FOLDER}/states"
SIMULATOR_STATE_SAVE_FILE = f"{STATES_FOLDER}/trading_state_history.json"

# Tentacle Config
STRATEGIES_REQUIRED_TIME_FRAME = "required_time_frames"
TRADING_MODE_REQUIRED_STRATEGIES = "required_strategies"
TRADING_MODE_REQUIRED_STRATEGIES_MIN_COUNT = "required_strategies_min_count"
STRATEGIES_REQUIRED_EVALUATORS = "required_evaluators"
TENTACLE_DEFAULT_CONFIG = "default_config"
TENTACLE_DEFAULT_FOLDER = "Default"
TENTACLE_UTIL_FOLDER = "Util"

# Web interface
UPDATED_CONFIG_SEPARATOR = "_"
GLOBAL_CONFIG_KEY = "global_config"
EVALUATOR_CONFIG_KEY = "evaluator_config"
DEACTIVATE_OTHERS = "deactivate_others"
TRADING_CONFIG_KEY = "trading_config"
COIN_MARKET_CAP_CURRENCIES_LIST_URL = "https://api.coinmarketcap.com/v2/listings/"

# Types
CONFIG_DICT_TYPE = NewType('ConfigDictType', Dict[str, Any])


class EvaluatorMatrixTypes(Enum):
    TA = "TA"
    SOCIAL = "SOCIAL"
    REAL_TIME = "REAL_TIME"
    STRATEGIES = "STRATEGIES"


class EvaluatorStates(Enum):
    SHORT = 1
    VERY_SHORT = 2
    LONG = 3
    VERY_LONG = 4
    NEUTRAL = 5


class PriceStrings(Enum):
    STR_PRICE_TIME = "time"
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


class OHLCVStrings(Enum):
    TIMESTAMP = "timestamp"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"


class PriceIndexes(Enum):
    IND_PRICE_TIME = 0
    IND_PRICE_OPEN = 1
    IND_PRICE_HIGH = 2
    IND_PRICE_LOW = 3
    IND_PRICE_CLOSE = 4
    IND_PRICE_VOL = 5


class TimeFrames(Enum):
    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    THREE_HOURS = "3h"
    FOUR_HOURS = "4h"
    HEIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


MIN_EVAL_TIME_FRAME = TimeFrames.FIVE_MINUTES

TimeFramesMinutes = {
    TimeFrames.ONE_MINUTE: 1,
    TimeFrames.THREE_MINUTES: 3,
    TimeFrames.FIVE_MINUTES: 5,
    TimeFrames.FIFTEEN_MINUTES: 15,
    TimeFrames.THIRTY_MINUTES: 30,
    TimeFrames.ONE_HOUR: 60,
    TimeFrames.TWO_HOURS: 120,
    TimeFrames.THREE_HOURS: 180,
    TimeFrames.FOUR_HOURS: 240,
    TimeFrames.HEIGHT_HOURS: 480,
    TimeFrames.TWELVE_HOURS: 720,
    TimeFrames.ONE_DAY: 1440,
    TimeFrames.THREE_DAYS: 4320,
    TimeFrames.ONE_WEEK: 10080,
    TimeFrames.ONE_MONTH: 43200,
}

# ladder : 1-100
TimeFramesRelevance = {
    TimeFrames.ONE_MINUTE: 5,
    TimeFrames.THREE_MINUTES: 5,
    TimeFrames.FIVE_MINUTES: 5,
    TimeFrames.FIFTEEN_MINUTES: 15,
    TimeFrames.THIRTY_MINUTES: 30,
    TimeFrames.ONE_HOUR: 50,
    TimeFrames.TWO_HOURS: 50,
    TimeFrames.FOUR_HOURS: 50,
    TimeFrames.HEIGHT_HOURS: 30,
    TimeFrames.TWELVE_HOURS: 30,
    TimeFrames.ONE_DAY: 30,
    TimeFrames.THREE_DAYS: 15,
    TimeFrames.ONE_WEEK: 15,
    TimeFrames.ONE_MONTH: 5,
}

IMAGE_ENDINGS = ["png", "jpg", "jpeg", "gif", "jfif", "tiff", "bmp", "ppm", "pgm", "pbm", "pnm", "webp", "hdr", "heif",
                 "bat", "bpg", "svg", "cgm"]


class TradeOrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class TradeOrderType(Enum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(Enum):
    FILLED = "closed"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    CLOSED = "closed"


class TraderOrderType(Enum):
    BUY_MARKET = 1
    BUY_LIMIT = 2
    TAKE_PROFIT = 3
    TAKE_PROFIT_LIMIT = 4
    STOP_LOSS = 5
    STOP_LOSS_LIMIT = 6
    SELL_MARKET = 7
    SELL_LIMIT = 8


class ExchangeConstantsTickersColumns(Enum):
    SYMBOL = "symbol"
    TIMESTAMP = "timestamp"
    DATETIME = "datetime"
    HIGH = "high"
    LOW = "low"
    BID = "bid"
    BID_VOLUME = "bidVolume"
    ASK = "ask"
    ASK_VOLUME = "askVolume"
    VWAP = "vwap"
    OPEN = "open"
    CLOSE = "close"
    LAST = "last"
    PREVIOUS_CLOSE = "previousClose"
    CHANGE = "change"
    PERCENTAGE = "percentage"
    AVERAGE = "average"
    BASE_VOLUME = "baseVolume"
    QUOTE_VOLUME = "quoteVolume"
    INFO = "info"


class ExchangeConstantsTickersInfoColumns(Enum):
    SYMBOL = "symbol"
    PRICE_CHANGE = "priceChange"
    PRICE_CHANGE_PERCENT = "priceChangePercent"
    WEIGHTED_AVERAGE_PRICE = "weightedAvgPrice"
    PREVIOUS_CLOSE_PRICE = "prevClosePrice"
    LAST_PRICE = "lastPrice"
    LAST_QUANTITY = "lastQty"
    BID_PRICE = "bidPrice"
    BID_QUANTITY = "bidQty"
    ASK_PRICE = "askPrice"
    ASK_QUANTITY = "askQty"
    OPEN_PRICE = "openPrice"
    HIGH_PRICE = "highPrice"
    LOW_PRICE = "lowPrice"
    VOLUME = "volume"
    QUOTE_VOLUME = "quoteVolume"
    OPEN_TIME = "openTime"
    CLOSE_TIME = "closeTime"
    FIRST_ID = "firstId"
    LAST_ID = "lastId"
    COUNT = "count"


class ExchangeConstantsMarketStatusColumns(Enum):
    SYMBOL = "symbol"
    ID = "id"
    CURRENCY = "base"
    MARKET = "quote"
    ACTIVE = "active"
    PRECISION = "precision"  # number of decimal digits "after the dot"
    PRECISION_PRICE = "price"
    PRECISION_AMOUNT = "amount"
    PRECISION_COST = "cost"
    LIMITS = "limits"  # value limits when placing orders on this market
    LIMITS_AMOUNT = "amount"
    LIMITS_AMOUNT_MIN = "min"  # order amount should be > min
    LIMITS_AMOUNT_MAX = "max"  # order amount should be < max
    LIMITS_PRICE = "price"  # same min/max limits for the price of the order
    LIMITS_PRICE_MIN = "min"  # order price should be > min
    LIMITS_PRICE_MAX = "max"  # order price should be < max
    LIMITS_COST = "cost"  # same limits for order cost = price * amount
    LIMITS_COST_MIN = "min"  # order cost should be > min
    LIMITS_COST_MAX = "max"  # order cost should be < max
    INFO = "info"


class ExchangeConstantsMarketStatusInfoColumns(Enum):
    # binance specific
    FILTERS = "filters"
    FILTER_TYPE = "filterType"
    PRICE_FILTER = "PRICE_FILTER"
    LOT_SIZE = "LOT_SIZE"
    MIN_PRICE = "minPrice"
    MAX_PRICE = "maxPrice"
    TICK_SIZE = "tickSize"
    MIN_QTY = "minQty"
    MAX_QTY = "maxQty"


class ExchangeConstantsOrderBookInfoColumns(Enum):
    BIDS = "bids"
    ASKS = "asks"
    TIMESTAMP = "timestamp"
    DATETIME = "datetime"
    NONCE = "nonce"


class ExchangeConstantsOrderColumns(Enum):
    INFO = "info"
    ID = "id"
    TIMESTAMP = "timestamp"
    DATETIME = 'datetime'
    LAST_TRADE_TIMESTAMP = "lastTradeTimestamp"
    SYMBOL = "symbol"
    TYPE = "type"
    SIDE = "side"
    PRICE = "price"
    AMOUNT = "amount"
    COST = "cost"
    AVERAGE = "average"
    FILLED = "filled"
    REMAINING = "remaining"
    STATUS = "status"
    FEE = "fee"
    TRADES = "trades"
    MAKER = "maker"
    TAKER = "taker"


class ExchangeConstantsFeesColumns(Enum):
    TYPE = "type"
    CURRENCY = "currency"
    RATE = "rate"
    COST = "cost"


class ExchangeConstantsMarketPropertyColumns(Enum):
    TAKER = "taker"  # trading
    MAKER = "maker"  # trading
    FEE = "fee"  # withdraw


class FeePropertyColumns(Enum):
    TYPE = "type"  # taker of maker
    CURRENCY = "currency"  # currency the fee is paid in
    RATE = "rate"  # multiplier applied to compute fee
    COST = "cost"  # fee amount


class PlatformsName(Enum):
    WINDOWS = "nt"
    LINUX = "posix"
    MAC = "mac"


class BacktestingDataFormats(Enum):
    REGULAR_COLLECTOR_DATA = 0
    KAIKO_DATA = 1


class OctoBotTypes(Enum):
    BINARY = "binary"
    PYTHON = "python"
    DOCKER = "docker"


class MetricsFields(Enum):
    ID = "_id"
    CURRENT_SESSION = "currentsession"
    STARTED_AT = "startedat"
    UP_TIME = "uptime"
    SIMULATOR = "simulator"
    TRADER = "trader"
    EVAL_CONFIG = "evalconfig"
    PAIRS = "pairs"
    EXCHANGES = "exchanges"
    NOTIFICATIONS = "notifications"
    TYPE = "type"
    PLATFORM = "platform"


# web user settings
DEFAULT_DISPLAY_TIME_FRAME = TimeFrames.ONE_HOUR
CONFIG_WATCHED_SYMBOLS = "watched_symbols"

OCTOBOT_KEY = b'uVEw_JJe7uiXepaU_DR4T-ThkjZlDn8Pzl8hYPIv7w0='
