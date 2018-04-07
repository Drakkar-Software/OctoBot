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
            self.pytrends.build_payload(kw_list=key_words, cat=0, timeframe=time_frame, geo='', gprop='')
        except ResponseError as e:
            self.logger.warn(str(e))

    def eval_impl(self):
        # Attention apparement limite de request / h assez faible
        try:
            interest_over_time_df = self.pytrends.interest_over_time()

            # TODO : too simple analysis
            first = interest_over_time_df.iloc[0, 0]
            last = interest_over_time_df.iloc[-1, 0]

            if first > 0:
                percent_diff = last / first
            else:
                percent_diff = last

            if percent_diff > 2:
                self.eval_note += 0.5
            elif percent_diff > 1:
                self.eval_note += 0.25
            elif percent_diff > 0.5:
                self.eval_note -= 0.25
            else:
                self.eval_note -= 0.5

        except Exception as e:
            self.logger.warn(str(e))

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
