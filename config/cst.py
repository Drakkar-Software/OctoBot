from enum import Enum

from evaluator.Social.forum_evaluator import *
from evaluator.Social.news_evaluator import *
from evaluator.Social.stats_evaluator import *
from evaluator.TA.momentum_evaluator import *
from evaluator.TA.orderbook_evaluator import *
from evaluator.TA.trend_evaluator import *
from evaluator.TA.volatility_evaluator import *


class PriceStrings(Enum):
    STR_PRICE_CLOSE = "<CLOSE>"
    STR_PRICE_OPEN = "<OPEN>"
    STR_PRICE_HIGH = "<HIGH>"
    STR_PRICE_LOW = "<LOW>"
    STR_PRICE_VOL = "<VOL>"


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


# TwitterNewsEvaluator()
# MediumNewsEvaluator()
# RedditForumEvaluator()
# BTCTalkForumEvaluator()
class SocialEvaluatorClasses(Enum):
    GoogleTrendStatsEvaluator()

class TAEvaluatorClasses(Enum):
    OBVMomentumEvaluator()
    RSIMomentumEvaluator()
    WhalesOrderBookEvaluator()
    ADXMomentumEvaluator()
    BBVolatilityEvaluator()
