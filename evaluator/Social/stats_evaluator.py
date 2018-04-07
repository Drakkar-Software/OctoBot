import talib
import numpy

from pytrends.exceptions import ResponseError
from pytrends.request import TrendReq

from config.cst import *
from evaluator.Social.social_evaluator import StatsSocialEvaluator, TimeFrames


class GoogleTrendStatsEvaluator(StatsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.pytrends = None
        self.enabled = True
        self.is_threaded = False

    # Use pytrends lib (https://github.com/GeneralMills/pytrends)
    # https://github.com/GeneralMills/pytrends/blob/master/examples/example.py
    def get_data(self):
        self.pytrends = TrendReq(hl='en-US', tz=0)
        #self.pytrends.GENERAL_URL = "https://trends.google.com/trends/explore"
        # self.symbol
        key_words = [self.symbol]
        try:
            # looks like only 1 and 3 months are working ...
            time_frame = "today " + str(self.social_config[STATS_EVALUATOR_HISTORY_TIME]) + "-m"
            # Attention apparement limite de request / h assez faible
            self.pytrends.build_payload(kw_list=key_words, cat=0, timeframe=time_frame, geo='', gprop='')
        except ResponseError as e:
            self.logger.warn(str(e))

    def eval_impl(self):
        interest_over_time_df = self.pytrends.interest_over_time()

        # compute bollinger bands
        upperband, middleband, lowerband = talib.BBANDS(interest_over_time_df[self.symbol])
        # if close to lowerband => no one is googling this cryptocurrency => low interest => bad,
        # therefore if close to middle, interest is keeping up => good
        # finally if up the middle one or even close to the upperband => very good

        current_interest = interest_over_time_df.iloc[-1, 0]
        current_up = upperband[-1]
        current_middle = middleband[-1]
        current_low = lowerband[-1]

        delta_up = current_up - current_middle
        delta_low = current_middle - current_low
        delta = numpy.sqrt(numpy.mean([delta_up, delta_low]))

        # best case: up the upperband
        if current_interest > current_up:
            self.eval_note = -1

        # worse case: down the lowerband
        elif current_interest < current_low:
            self.eval_note = 1

        # average case: approximately on middleband
        elif current_middle + delta > current_interest and current_middle - delta < current_interest:
            micro_change = numpy.sqrt(current_interest/current_middle) - 1
            self.eval_note = -1 * micro_change

        # good case: up the middleband
        elif current_middle + delta < current_interest:
            self.eval_note = -1 * (current_interest / delta_up)

        # bad case: down the lowerband
        elif current_middle + delta < current_interest:
            self.eval_note = current_interest / delta_low

    def run(self):
        pass

    # check if history is not too high
    def load_config(self):
        super(GoogleTrendStatsEvaluator, self).load_config()
        if self.social_config[STATS_EVALUATOR_HISTORY_TIME] > STATS_EVALUATOR_MAX_HISTORY_TIME:
            self.social_config[STATS_EVALUATOR_HISTORY_TIME] = STATS_EVALUATOR_MAX_HISTORY_TIME

    def set_default_config(self):
        self.social_config = {
            CONFIG_REFRESH_RATE: 3600,
            STATS_EVALUATOR_HISTORY_TIME: 3
        }
