import logging

from evaluator.Strategies import StrategiesEvaluator
from evaluator.Social import SocialEvaluator
from evaluator.RealTime import RealTimeTAEvaluator
from evaluator.TA import TAEvaluator


class EvaluatorCreator:

    @staticmethod
    def create_ta_eval_list(evaluator):
        ta_eval_list = []
        for ta_type in TAEvaluator.__subclasses__():
            for ta_eval_class_type in ta_type.__subclasses__():
                ta_eval_class = ta_eval_class_type()
                if ta_eval_class.get_is_enabled():
                    ta_eval_class.set_logger(logging.getLogger(ta_eval_class_type.get_name()))
                    ta_eval_class.set_config(evaluator.config)
                    ta_eval_class.set_data(evaluator.data)

                    ta_eval_list.append(ta_eval_class)

        return ta_eval_list

    @staticmethod
    def create_unique_eval(config):
        unique_eval_list = []
        for social_type in SocialEvaluator.__subclasses__():
            for social_eval_class_type in social_type.__subclasses__():
                unique_eval_class = social_eval_class_type()
                if unique_eval_class.get_is_enabled() and social_eval_class_type.get_is_unique_evaluator_dispatcher():
                    unique_eval_class.set_logger(logging.getLogger(social_eval_class_type.get_name()))
                    unique_eval_class.set_config(config)
                    unique_eval_class.prepare()

                    # start refreshing thread
                    if unique_eval_class.get_is_threaded():
                        unique_eval_class.start()

                    unique_eval_list.append(unique_eval_class)
        return unique_eval_list

    @staticmethod
    def create_social_eval(config, symbol, unique_eval_list):
        social_eval_list = []
        for social_type in SocialEvaluator.__subclasses__():
            for social_eval_class_type in social_type.__subclasses__():
                social_eval_class = social_eval_class_type()
                if social_eval_class.get_is_enabled():
                    social_eval_class.set_logger(logging.getLogger(social_eval_class_type.get_name()))
                    social_eval_class.set_config(config)
                    social_eval_class.set_symbol(symbol)
                    social_eval_class.prepare()

                    if social_eval_class_type.get_is_client_to_unique_evaluator():
                        for unique_evaluator_dispatcher in unique_eval_list:
                            if social_eval_class.is_client_to_this_dispatcher(unique_evaluator_dispatcher):
                                unique_evaluator_dispatcher.register_client(symbol, social_eval_class)

                    # start refreshing thread if the thread is not unique
                    elif social_eval_class.get_is_threaded():
                        social_eval_class.start()

                    social_eval_list.append(social_eval_class)

        return social_eval_list

    @staticmethod
    def create_real_time_TA_evals(config, exchange_inst, symbol):
        real_time_ta_eval_list = []
        for real_time_class_type in RealTimeTAEvaluator.__subclasses__():
            real_time_eval_class = real_time_class_type(exchange_inst, symbol)
            if real_time_eval_class.get_is_enabled():
                real_time_eval_class.set_logger(logging.getLogger(real_time_class_type.get_name()))
                real_time_eval_class.set_config(config)

                # start refreshing thread
                real_time_eval_class.start()

                real_time_ta_eval_list.append(real_time_eval_class)

        return real_time_ta_eval_list

    @staticmethod
    def create_social_not_threaded_list(social_eval_list):
        social_eval_not_threaded_list = []
        for social_eval in social_eval_list:

            # if not threaded --> ask him to refresh with generic thread
            if not social_eval.get_is_threaded():
                social_eval_not_threaded_list.append(social_eval)

        return social_eval_not_threaded_list

    @staticmethod
    def create_strategies_eval_list():
        strategies_eval_list = []
        for strategies_type in StrategiesEvaluator.__subclasses__():
            for strategies_eval_class_type in strategies_type.__subclasses__():
                strategies_eval_class = strategies_eval_class_type()
                if strategies_eval_class.get_is_enabled():
                    strategies_eval_class.set_logger(logging.getLogger(strategies_eval_class.get_name()))

                    strategies_eval_list.append(strategies_eval_class)

        return strategies_eval_list
