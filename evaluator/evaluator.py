from evaluator.Social_evaluator import *


class Evaluator:
    def __init__(self):
        self.config = None
        self.symbol = None
        self.history_time = None
        self.data = None
        self.symbol = None
        self.social_eval_list = []

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
        for social_eval_class in SocialEvaluatorClasses:
            social_eval_class.set_config(self.config)
            social_eval_class.set_history_time(self.history_time)
            social_eval_class.set_symbol(self.symbol)
            self.social_eval_list.append(social_eval_class._eval())

        print(self.social_eval_list)
