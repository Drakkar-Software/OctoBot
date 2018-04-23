import logging

from evaluator.RealTime import RealTimeEvaluator
from evaluator.Social import SocialEvaluator
from evaluator.Strategies import StrategiesEvaluator
from evaluator.TA import TAEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Dispatchers.abstract_dispatcher import AbstractDispatcher


class EvaluatorCreator:

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    def create_advanced_evaluators(evaluator_class, config):
        evaluator_advanced_eval_class_list = []
        for evaluator_subclass in evaluator_class.__subclasses__():
            for eval_class in evaluator_subclass.__subclasses__():
                for eval_class_type in AdvancedManager.get_classes(config, eval_class):
                    evaluator_advanced_eval_class_list.append(eval_class_type)
        return evaluator_advanced_eval_class_list

    @staticmethod
    def create_ta_eval_list(evaluator):
        ta_eval_instance_list = []
        for ta_eval_class in EvaluatorCreator.create_advanced_evaluators(TAEvaluator, evaluator.get_config()):
            ta_eval_class_instance = ta_eval_class()
            if ta_eval_class_instance.get_is_enabled():
                ta_eval_class_instance.set_logger(logging.getLogger(ta_eval_class.get_name()))
                ta_eval_class_instance.set_config(evaluator.config)
                ta_eval_class_instance.set_data(evaluator.data)
                ta_eval_class_instance.set_symbol(evaluator.get_symbol())
                ta_eval_instance_list.append(ta_eval_class_instance)

        return ta_eval_instance_list

    @staticmethod
    def create_dispatchers(config):
        dispatchers_list = []
        for dispatcher_class in AbstractDispatcher.__subclasses__():
            dispatcher_instance = dispatcher_class(config)
            if dispatcher_instance.get_is_setup_correctly():
                dispatchers_list.append(dispatcher_instance)
        return dispatchers_list

    @staticmethod
    def create_social_eval(config, symbol, dispatchers_list):
        social_eval_list = []
        for social_eval_class in EvaluatorCreator.create_advanced_evaluators(SocialEvaluator, config):
            social_eval_class_instance = social_eval_class()
            if social_eval_class_instance.get_is_enabled():
                is_evaluator_to_be_used = True
                social_eval_class_instance.set_logger(logging.getLogger(social_eval_class.get_name()))
                social_eval_class_instance.set_config(config)
                social_eval_class_instance.set_symbol(symbol)
                social_eval_class_instance.prepare()

                # If evaluator is a dispatcher client --> check if dispatcher exists
                # else warn and pass this evaluator
                if social_eval_class.get_is_dispatcher_client():
                    client_found_dispatcher = EvaluatorCreator.set_social_eval_dispatcher(social_eval_class_instance,
                                                                                          dispatchers_list)
                    if not client_found_dispatcher:
                        is_evaluator_to_be_used = False
                        logging.getLogger(EvaluatorCreator.get_name()).warning(
                            "No dispatcher found for evaluator: {0} for symbol: {1}, evaluator has been disabled."
                                .format(social_eval_class_instance.get_name(), symbol))

                # start refreshing thread if the thread is not manage by dispatcher
                elif is_evaluator_to_be_used and social_eval_class_instance.get_is_threaded():
                    social_eval_class_instance.start()

                if is_evaluator_to_be_used:
                    social_eval_list.append(social_eval_class_instance)

        return social_eval_list

    @staticmethod
    def set_social_eval_dispatcher(social_eval_class_instance, dispatchers_list):
        for evaluator_dispatcher in dispatchers_list:
            if social_eval_class_instance.is_client_to_this_dispatcher(evaluator_dispatcher):
                social_eval_class_instance.set_dispatcher(evaluator_dispatcher)
                evaluator_dispatcher.register_client(social_eval_class_instance)
                return True
        return False

    @staticmethod
    def create_real_time_ta_evals(config, exchange_inst, symbol):
        real_time_ta_eval_list = []
        for real_time_eval_class in EvaluatorCreator.create_advanced_evaluators(RealTimeEvaluator, config):
            real_time_eval_class_instance = real_time_eval_class(exchange_inst, symbol)
            if real_time_eval_class_instance.get_is_enabled():
                real_time_eval_class_instance.set_logger(logging.getLogger(real_time_eval_class.get_name()))
                real_time_eval_class_instance.set_config(config)

                # start refreshing thread
                real_time_eval_class_instance.start()

                real_time_ta_eval_list.append(real_time_eval_class_instance)

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
    def create_strategies_eval_list(config):
        strategies_eval_list = []
        for strategies_eval_class in EvaluatorCreator.create_advanced_evaluators(StrategiesEvaluator, config):
            strategies_eval_class_instance = strategies_eval_class()
            if strategies_eval_class_instance.get_is_enabled():
                strategies_eval_class_instance.set_logger(
                    logging.getLogger(strategies_eval_class_instance.get_name()))

                strategies_eval_list.append(strategies_eval_class_instance)

        return strategies_eval_list
