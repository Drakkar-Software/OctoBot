from evaluator.Social import *
from evaluator.TA import *


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
        self.social_eval_list = []
        for social_type in SocialEvaluator.__subclasses__():
            for social_eval_class_type in social_type.__subclasses__():
                social_eval_class = social_eval_class_type()
                social_eval_class.set_config(self.config)
                social_eval_class.set_history_time(self.history_time)
                social_eval_class.set_symbol(self.symbol)

                social_eval_class.get_data()
                self.social_eval_list.append(social_eval_class.eval())

        return self.social_eval_list

    def ta_eval(self):
        self.ta_eval_list = []
        for ta_type in TAEvaluator.__subclasses__():
            for ta_eval_class_type in ta_type.__subclasses__():
                ta_eval_class = ta_eval_class_type()
                ta_eval_class.set_config(self.config)
                ta_eval_class.set_data(self.data)

                self.ta_eval_list.append(ta_eval_class.eval())

        return self.ta_eval_list
