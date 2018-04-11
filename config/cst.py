from enum import Enum

from aenum import MultiValueEnum

MINUTE_TO_SECONDS = 60
START_EVAL_NOTE = 0
START_EVAL_PERTINENCE = 1

MARKET_SEPARATOR = "/"

SPECIFIC_CONFIG_PATH = "config/specific_evaluator_config/"
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_TIME_FRAME = "time_frame"
CONFIG_FILE_EXT = ".json"
CONFIG_CRYPTO_CURRENCIES = "crypto_currencies"
CONFIG_CRYPTO_PAIRS = "pairs"
CONFIG_CRYPTO_TWITTERS = "twitters"

# DEBUG
CONFIG_DEBUG_OPTION_PERF = "PERF"
CONFIG_DEBUG_OPTION = "DEBUG"

CONFIG_ENABLED_OPTION = "enabled"

CONFIG_CATEGORY_NOTIFICATION = "notification"
CONFIG_CATEGORY_SERVICES = "services"

SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE = 1

STATS_EVALUATOR_HISTORY_TIME = "relevant_history_months"
STATS_EVALUATOR_MAX_HISTORY_TIME = 3

ORDER_REFRESHER_TIME = 30

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


class TimeFramesMinutes(MultiValueEnum):
    ONE_MINUTE = 1, TimeFrames.ONE_MINUTE
    THREE_MINUTES = 3, TimeFrames.THREE_MINUTES
    FIVE_MINUTES = 5, TimeFrames.FIVE_MINUTES
    FIFTEEN_MINUTES = 15, TimeFrames.FIFTEEN_MINUTES
    THIRTY_MINUTES = 30, TimeFrames.THIRTY_MINUTES
    ONE_HOUR = 60, TimeFrames.ONE_HOUR
    TWO_HOURS = 120, TimeFrames.TWO_HOURS
    FOUR_HOURS = 240, TimeFrames.FOUR_HOURS
    HEIGHT_HOURS = 480, TimeFrames.HEIGHT_HOURS
    TWELVE_HOURS = 720, TimeFrames.TWELVE_HOURS
    ONE_DAY = 1440, TimeFrames.ONE_DAY
    THREE_DAYS = 4320, TimeFrames.THREE_DAYS
    ONE_WEEK = 10080, TimeFrames.ONE_WEEK
    ONE_MONTH = 43200, TimeFrames.ONE_MONTH


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
