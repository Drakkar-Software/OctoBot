import operator
from enum import Enum

VERSION = "0.0.8-alpha"

MINUTE_TO_SECONDS = 60
HOURS_TO_SECONDS = MINUTE_TO_SECONDS * 60
DAYS_TO_SECONDS = HOURS_TO_SECONDS * 24

CONFIG_GLOBAL_UTILS = "global_utils"
CONFIG_ENABLED_OPTION = "enabled"
CONFIG_SYMBOL = "symbol"

# Files
CONFIG_FILE = "config/config.json"
CONFIG_EVALUATOR_FILE = "config/evaluator_config.json"

# Advanced
CONFIG_ADVANCED_CLASSES = "advanced_classes"
CONFIG_ADVANCED_INSTANCES = "advanced_instances"

# Backtesting
CONFIG_BACKTESTING = "backtesting"
CONFIG_BACKTESTING_DATA_FILE = "file"

# Data collector
CONFIG_DATA_COLLECTOR = "data_collector"
DATA_COLLECTOR_REFRESHER_TIME = 10
CONFIG_DATA_COLLECTOR_PATH = "backtesting/collector/data/"

# Trading
CONFIG_EXCHANGES = "exchanges"
CONFIG_TRADER = "trader"
CONFIG_SIMULATOR = "simulator"
CONFIG_STARTING_PORTFOLIO = "starting_portfolio"
CONFIG_TRADER_RISK = "risk"
CONFIG_TRADER_RISK_MIN = 0.05
CONFIG_TRADER_RISK_MAX = 1
ORDER_REFRESHER_TIME = 5
SIMULATOR_LAST_PRICES_TO_CHECK = 10
# e-7
MARKET_MIN_PORTFOLIO_CREATE_ORDER = 0.0000001
CURRENCY_MIN_PORTFOLIO_CREATE_ORDER = 0.0000001
CONFIG_TRADER_REFERENCE_MARKET = "reference_market"
DEFAULT_REFERENCE_MARKET = "BTC"
MARKET_SEPARATOR = "/"

# Notification
CONFIG_NOTIFICATION_INSTANCE = "notifier"
CONFIG_CATEGORY_NOTIFICATION = "notification"
NOTIFICATION_STARTING_MESSAGE = "CryptoBot v{0} starting...".format(VERSION)
NOTIFICATION_STOPPING_MESSAGE = "CryptoBot v{0} stopping...".format(VERSION)

# DEBUG options
CONFIG_DEBUG_OPTION_PERF = "Performance_analyser"
CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN = 5
CONFIG_DEBUG_OPTION = "DEBUG"

# SERVICES
CONFIG_CATEGORY_SERVICES = "services"
CONFIG_SERVICE_INSTANCE = "service_instance"

# gmail
CONFIG_GMAIL = "gmail"

# twitter
CONFIG_TWITTERS_ACCOUNTS = "accounts"
CONFIG_TWITTERS_HASHTAGS = "hashtags"
CONFIG_TWITTER = "twitter"
CONFIG_REDDIT = "reddit"
CONFIG_REDDIT_SUBREDDITS = "subreddits"
CONFIG_REDDIT_ENTRY = "entry"
CONFIG_REDDIT_ENTRY_WEIGHT = "entry_weight"
CONFIG_TWITTER_API_INSTANCE = "twitter_api_instance"
CONFIG_TWEET = "tweet"
CONFIG_TWEET_DESCRIPTION = "tweet_description"

# Evaluator
CONFIG_EVALUATOR = "evaluator"
SPECIFIC_CONFIG_PATH = "config/specific_evaluator_config/"
START_PENDING_EVAL_NOTE = "0"  # force exception
INIT_EVAL_NOTE = 0
START_EVAL_PERTINENCE = 1
MAX_TA_EVAL_TIME_SECONDS = 0.1
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_TIME_FRAME = "time_frame"
CONFIG_FILE_EXT = ".json"
CONFIG_CRYPTO_CURRENCIES = "crypto_currencies"
CONFIG_CRYPTO_PAIRS = "pairs"

# Socials
SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE = 1

# Stats
STATS_EVALUATOR_HISTORY_TIME = "relevant_history_months"
STATS_EVALUATOR_MAX_HISTORY_TIME = 3

# Tools
DIVERGENCE_USED_VALUE = 30


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


class EvaluatorsPertinence(Enum):
    SocialEvaluator = 0  # temp
    TAEvaluator = 1


class PriceStrings(Enum):
    STR_PRICE_TIME = "time"
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


class PriceIndexes(Enum):
    IND_PRICE_TIME = 0
    IND_PRICE_CLOSE = 4
    IND_PRICE_OPEN = 1
    IND_PRICE_HIGH = 2
    IND_PRICE_LOW = 3
    IND_PRICE_VOL = 5


class TimeFrames(Enum):
    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    HEIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


TimeFramesMinutes = {
    TimeFrames.ONE_MINUTE: 1,
    TimeFrames.THREE_MINUTES: 3,
    TimeFrames.FIVE_MINUTES: 5,
    TimeFrames.FIFTEEN_MINUTES: 15,
    TimeFrames.THIRTY_MINUTES: 30,
    TimeFrames.ONE_HOUR: 60,
    TimeFrames.TWO_HOURS: 120,
    TimeFrames.FOUR_HOURS: 240,
    TimeFrames.HEIGHT_HOURS: 480,
    TimeFrames.TWELVE_HOURS: 720,
    TimeFrames.ONE_DAY: 1440,
    TimeFrames.THREE_DAYS: 4320,
    TimeFrames.ONE_WEEK: 10080,
    TimeFrames.ONE_MONTH: 43200,
}

TimeFramesRank = sorted(TimeFramesMinutes, key=TimeFramesMinutes.__getitem__)

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
    BUY = 1
    SELL = 2


class OrderStatus(Enum):
    FILLED = 1
    PENDING = 2


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
