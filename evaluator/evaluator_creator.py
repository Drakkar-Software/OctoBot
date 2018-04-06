import logging

from evaluator.Rules import RulesEvaluator
from evaluator.Social import SocialEvaluator
from evaluator.RealTime import RealTimeTAEvaluator
from evaluator.TA import TAEvaluator


class EvaluatorCreator:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.social_eval_list = []
        self.ta_eval_list = []
        self.social_eval_not_threaded_list = []
        self.real_time_eval_list = []
        self.rules_eval_list = []

    def get_social_eval_list(self):
        return self.social_eval_list

    def get_real_time_eval_list(self):
        return self.real_time_eval_list

    def get_ta_eval_list(self):
        return self.ta_eval_list

    def get_rules_eval_list(self):
        return self.rules_eval_list

    def get_social_eval_not_threaded_list(self):
        return self.social_eval_not_threaded_list

    def set_social_eval(self, new_social_list, evaluator_thread):
        self.social_eval_list = new_social_list
        for social_eval in self.social_eval_list:
            social_eval.add_evaluator_thread(evaluator_thread)

    def set_real_time_eval(self, new_real_time_list, evaluator_thread):
        self.real_time_eval_list = new_real_time_list
        for real_time_eval in self.real_time_eval_list:
            real_time_eval.add_evaluator_thread(evaluator_thread)

    @staticmethod
    def create_social_eval(config, symbol):
        social_eval_list = []
        for social_type in SocialEvaluator.__subclasses__():
            for social_eval_class_type in social_type.__subclasses__():
                social_eval_class = social_eval_class_type()
                if social_eval_class.get_is_enabled():
                    social_eval_class.set_logger(logging.getLogger(social_eval_class_type.get_name()))
                    social_eval_class.set_config(config)
                    social_eval_class.set_symbol(symbol)

                    # start refreshing thread
                    if social_eval_class.get_is_threaded():
                        social_eval_class.start()

                    social_eval_list.append(social_eval_class)

        return social_eval_list

    @staticmethod
    def create_real_time_TA_evals(config, exchange_inst, symbol):
        real_time_TA_eval_list = []
        for real_time_class_type in RealTimeTAEvaluator.__subclasses__():
            real_time_eval_class = real_time_class_type(exchange_inst, symbol)
            if real_time_eval_class.get_is_enabled():
                real_time_eval_class.set_logger(logging.getLogger(real_time_class_type.get_name()))
                real_time_eval_class.set_config(config)

                # start refreshing thread
                real_time_eval_class.start()

                real_time_TA_eval_list.append(real_time_eval_class)

        return real_time_TA_eval_list

    def create_social_not_threaded_list(self):
        for social_eval in self.get_social_eval_list():

            # if not threaded --> ask him to refresh with generic thread
            if not social_eval.get_is_threaded():
                self.social_eval_not_threaded_list.append(social_eval)

        return self.social_eval_not_threaded_list

    def create_ta_eval_list(self):
        if not self.ta_eval_list:
            for ta_type in TAEvaluator.__subclasses__():
                for ta_eval_class_type in ta_type.__subclasses__():
                    ta_eval_class = ta_eval_class_type()
                    if ta_eval_class.get_is_enabled():
                        ta_eval_class.set_logger(logging.getLogger(ta_eval_class_type.get_name()))
                        ta_eval_class.set_config(self.evaluator.config)
                        ta_eval_class.set_data(self.evaluator.data)

                        self.ta_eval_list.append(ta_eval_class)

        return self.ta_eval_list

    def create_rules_eval_list(self):
        if not self.rules_eval_list:
            for rules_type in RulesEvaluator.__subclasses__():
                for rules_eval_class_type in rules_type.__subclasses__():
                    rules_eval_class = rules_eval_class_type()
                    if rules_eval_class.get_is_enabled():
                        rules_eval_class.set_logger(logging.getLogger(rules_eval_class.get_name()))
                        rules_eval_class.set_config(self.evaluator.config)

                        self.rules_eval_list.append(rules_eval_class)

        return self.rules_eval_list
