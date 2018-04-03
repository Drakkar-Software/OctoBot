from pytrends.exceptions import ResponseError
from pytrends.request import TrendReq

from evaluator.Social.Social_evaluator import StatsSocialEvaluator, TimeFrames


class GoogleTrendStatsEvaluator(StatsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.pytrends = None
        self.enabled = False

    # Use pytrends lib (https://github.com/GeneralMills/pytrends)
    # https://github.com/GeneralMills/pytrends/blob/master/examples/example.py
    def get_data(self):
        self.pytrends = TrendReq(hl='en-US', tz=0)
        # self.symbol
        kw_list = ["bitcoin"]
        try:
            if self.history_time < TimeFrames.ONE_DAY.value:
                # 4 hours history
                time_frame = "now 4-H"
            elif self.history_time < TimeFrames.ONE_WEEK.value:
                # 7 days history
                time_frame = "now 7-d"
            else:
                # 3 months history
                time_frame = "today 3-m"
            self.pytrends.build_payload(kw_list, cat=0, timeframe=time_frame, geo='', gprop='')
        except ResponseError as e:
            self.logger.warn(str(e))

    def eval(self):
        # Attention apparement limite de request / h assez faible
        try:
            interest_over_time_df = self.pytrends.interest_over_time()

            # TODO : too simple analysis
            first = interest_over_time_df.iloc[0, 0]
            last = interest_over_time_df.iloc[-1, 0]

            if first > 0:
                percent_diff = last/first
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
