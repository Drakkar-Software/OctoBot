from config.cst import EvaluatorClasses
from evaluator.Social.forum_evaluator import ForumSocialEvaluatorClasses
from evaluator.Social.news_evaluator import NewsSocialEvaluatorClasses
from evaluator.Social.stats_evaluator import StatsSocialEvaluatorClasses
from evaluator.TA.momentum_evaluator import MomentumEvaluatorClasses
from evaluator.TA.orderbook_evaluator import OrderBookEvaluatorClasses
from evaluator.TA.trend_evaluator import TrendEvaluatorClasses
from evaluator.TA.volatility_evaluator import VolatilityEvaluatorClasses


class Evaluator:
    def __init__(self):
        self.config = None
        self.symbol = None
        self.history_time = None
        self.data = None
        self.symbol = None

        self.social_eval_list = []
        self.ta_eval_list = []

    def set_config(self, config):
        self.config = config

    def set_data(self, data):
        self.data = data

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_history_time(self, history_time):
        self.history_time = history_time

    def social_eval(self):
        for social_type in SocialEvaluatorClasses().get_classes():
            for social_eval_class in social_type.get_classes():
                social_eval_class.set_config(self.config)
                social_eval_class.set_history_time(self.history_time)
                social_eval_class.set_symbol(self.symbol)

                social_eval_class.get_data()
                self.social_eval_list.append(social_eval_class.eval())

        print(self.social_eval_list)

    def ta_eval(self):
        for ta_type in TAEvaluatorClasses().get_classes():
            for ta_eval_class in ta_type.get_classes():
                ta_eval_class.set_config(self.config)
                ta_eval_class.set_data(self.data)

                self.ta_eval_list.append(ta_eval_class.eval())

        print(self.ta_eval_list)


# TODO : TEMP LOCATION
class SocialEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            StatsSocialEvaluatorClasses(),
            ForumSocialEvaluatorClasses(),
            NewsSocialEvaluatorClasses()
        ]


# TODO : TEMP LOCATION
class TAEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            VolatilityEvaluatorClasses(),
            TrendEvaluatorClasses(),
            OrderBookEvaluatorClasses(),
            MomentumEvaluatorClasses()
        ]
