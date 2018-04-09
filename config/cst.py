from enum import Enum

MARKET_SEPARATOR = "/"

MINUTE_TO_SECONDS = 60
START_EVAL_NOTE = 0
START_EVAL_PERTINENCE = 1

SPECIFIC_CONFIG_PATH = "config/specific_evaluator_config/"
CONFIG_REFRESH_RATE = "refresh_rate_seconds"
CONFIG_TIME_FRAME = "time_frame"
CONFIG_FILE_EXT = ".json"
CONFIG_CRYPTO_CURRENCIES = "crypto_currencies"

SOCIAL_EVALUATOR_NOT_THREADED_UPDATE_RATE = 1

STATS_EVALUATOR_HISTORY_TIME = "relevant_history_months"
STATS_EVALUATOR_MAX_HISTORY_TIME = 3


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
    STR_PRICE_CLOSE = "close"
    STR_PRICE_OPEN = "open"
    STR_PRICE_HIGH = "high"
    STR_PRICE_LOW = "low"
    STR_PRICE_VOL = "vol"


class TimeFrames(Enum):
    ONE_MINUTE = 1
    FIVE_MINUTES = 5
    THIRTY_MINUTES = 30
    ONE_HOUR = 60
    TWO_HOURS = 120
    FOUR_HOURS = 240
    ONE_DAY = 1440
    THREE_DAYS = 4320
    ONE_WEEK = 10080
    ONE_MONTH = 43200


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


# TODO : review
class TimeFramePertinence(Enum):
    ONE_MINUTE = 1, TimeFrames.ONE_MINUTE
    FIVE_MINUTES = 1, TimeFrames.FIVE_MINUTES
    THIRTY_MINUTES = 1, TimeFrames.THIRTY_MINUTES
    ONE_HOUR = 1, TimeFrames.ONE_HOUR
    TWO_HOURS = 1, TimeFrames.TWO_HOURS
    FOUR_HOURS = 1, TimeFrames.FOUR_HOURS
    ONE_DAY = 1, TimeFrames.ONE_DAY
    THREE_DAYS = 1, TimeFrames.THREE_DAYS
    ONE_WEEK = 1, TimeFrames.ONE_WEEK
    ONE_MONTH = 1, TimeFrames.ONE_MONTH
