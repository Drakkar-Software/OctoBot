from pytrends.request import TrendReq

from evaluator.Social_evaluator import StatsSocialEvaluator


class GoogleTrendStatsEvaluator(StatsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.pytrends = TrendReq(hl='en-US', tz=self.history_time)

    # Use pytrends lib (https://github.com/GeneralMills/pytrends)
    # https://github.com/GeneralMills/pytrends/blob/master/examples/example.py
    def get_data(self):
        kw_list = [self.symbol]
        # self.pytrends.build_payload(kw_list, cat=0, timeframe='today 5-y', geo='', gprop='')

    def eval(self):
        # Attention apparement limite de request / h assez faible
        # interest_over_time_df = self.pytrends.interest_over_time()
        # print(interest_over_time_df.head())
        return 0
