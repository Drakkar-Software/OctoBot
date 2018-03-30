from pytrends.request import TrendReq

from evaluator.Social_evaluator import StatsEvaluator


class GoogleTrendStatsEvaluator(StatsEvaluator):
    def __init__(self):
        super().__init__()
        self.pytrends = TrendReq(hl='en-US', tz=self.history_time)

    # Use pytrends lib (https://github.com/GeneralMills/pytrends)
    def get_data(self):
        kw_list = [self.symbol]
        self.pytrends.build_payload(kw_list, cat=0, timeframe='today 5-y', geo='', gprop='')
        # self.pytrends.interest_by_region(resolution='COUNTRY')

    def eval(self):
        return self.pytrends.interest_over_time()
