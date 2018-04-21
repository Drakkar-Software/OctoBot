from enum import Enum

VERSION = "0.0.7-alpha"

MINUTE_TO_SECONDS = 60
START_PENDING_EVAL_NOTE = "0"  # force exception
INIT_EVAL_NOTE = 0
START_EVAL_PERTINENCE = 1

MARKET_SEPARATOR = "/"

CONFIG_FILE = "config/config.json"
CONFIG_GLOBAL_UTILS = "global_utils"
CONFIG_ADVANCED_CLASSES = "advanced_classes"
CONFIG_ADVANCED_INSTANCES = "advanced_instances"
SPECIFIC_CONFIG_PATH = "config/specific_evaluator_config/"
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_TIME_FRAME = "time_frame"
CONFIG_FILE_EXT = ".json"
CONFIG_CRYPTO_CURRENCIES = "crypto_currencies"
CONFIG_CRYPTO_PAIRS = "pairs"

# gmail
CONFIG_GMAIL = "gmail"

# twitter
CONFIG_TWITTERS_ACCOUNTS = "accounts"
CONFIG_TWITTERS_HASHTAGS = "hashtags"
CONFIG_TWITTER = "twitter"
CONFIG_TWITTER_API_INSTANCE = "twitter_api_instance"
CONFIG_ADDITIONAL_RESOURCES = "additional_resources"
CONFIG_TWEET = "tweet"
CONFIG_TWEET_DESCRIPTION = "tweet_description"

# DEBUG
CONFIG_DEBUG_OPTION_PERF = "PERF"
CONFIG_DEBUG_OPTION_PERF_REFRESH_TIME_MIN = 5
CONFIG_DEBUG_OPTION = "DEBUG"

CONFIG_ENABLED_OPTION = "enabled"

CONFIG_TRADER = "trader"
CONFIG_SIMULATOR = "simulator"
CONFIG_STARTING_PORTFOLIO = "starting_portfolio"
CONFIG_NOTIFICATION_INSTANCE = "notifier"
CONFIG_CATEGORY_NOTIFICATION = "notification"
CONFIG_CATEGORY_SERVICES = "services"
CONFIG_SERVICE_INSTANCE = "service_instance"

CONFIG_TRADER_RISK = "risk"
CONFIG_TRADER_RISK_MIN = 0.05

SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE = 1

STATS_EVALUATOR_HISTORY_TIME = "relevant_history_months"
STATS_EVALUATOR_MAX_HISTORY_TIME = 3

ORDER_REFRESHER_TIME = 5
SIMULATOR_LAST_PRICES_TO_CHECK = 10

CONFIG_TRADER_REFERENCE_MARKET = "reference_market"
DEFAULT_REFERENCE_MARKET = "BTC"

DIVERGENCE_USED_VALUE = 30


class EvaluatorRisk(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


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
