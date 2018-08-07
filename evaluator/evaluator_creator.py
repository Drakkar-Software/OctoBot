import logging

from evaluator.RealTime import RealTimeEvaluator
from evaluator.Social import SocialEvaluator
from evaluator.Strategies import StrategiesEvaluator
from evaluator.TA import TAEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Dispatchers.abstract_dispatcher import AbstractDispatcher
from config.cst import CONFIG_TIME_FRAME, CONFIG_EVALUATORS_WILDCARD
from tools.time_frame_manager import TimeFrameManager


class EvaluatorCreator:

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    def create_ta_eval_list(evaluator, relevant_evaluators):
        ta_eval_instance_list = []
        for ta_eval_class in AdvancedManager.create_advanced_evaluator_types_list(TAEvaluator, evaluator.get_config()):
            ta_eval_class_instance = ta_eval_class()
            ta_eval_class_instance.set_config(evaluator.config)
            if EvaluatorCreator.is_relevant_evaluator(ta_eval_class_instance, relevant_evaluators):
                ta_eval_class_instance.set_logger(logging.getLogger(ta_eval_class.get_name()))
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
    def create_social_eval(config, symbol, dispatchers_list, relevant_evaluators):
        social_eval_list = []
        for social_eval_class in AdvancedManager.create_advanced_evaluator_types_list(SocialEvaluator, config):
            social_eval_class_instance = social_eval_class()
            social_eval_class_instance.set_config(config)
            if EvaluatorCreator.is_relevant_evaluator(social_eval_class_instance, relevant_evaluators):
                is_evaluator_to_be_used = True
                social_eval_class_instance.set_logger(logging.getLogger(social_eval_class.get_name()))
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
    def create_real_time_ta_evals(config, exchange_inst, symbol, relevant_evaluators):
        real_time_ta_eval_list = []
        for real_time_eval_class in AdvancedManager.create_advanced_evaluator_types_list(RealTimeEvaluator, config):
            real_time_eval_class_instance = real_time_eval_class(exchange_inst, symbol)
            real_time_eval_class_instance.set_config(config)
            if EvaluatorCreator.is_relevant_evaluator(real_time_eval_class_instance, relevant_evaluators):
                real_time_eval_class_instance.set_logger(logging.getLogger(real_time_eval_class.get_name()))

                # start refreshing thread
                real_time_eval_class_instance.start()

                real_time_ta_eval_list.append(real_time_eval_class_instance)

        return real_time_ta_eval_list

    @staticmethod
    def create_social_not_threaded_list(social_eval_list):
        # if not threaded --> ask him to refresh with generic thread
        return [
            social_eval
            for social_eval in social_eval_list
            if not social_eval.get_is_threaded()
        ]

    @staticmethod
    def create_strategies_eval_list(config):
        strategies_eval_list = []
        for strategies_eval_class in AdvancedManager.create_advanced_evaluator_types_list(StrategiesEvaluator, config):
            strategies_eval_class_instance = strategies_eval_class()
            strategies_eval_class_instance.set_config(config)
            if strategies_eval_class_instance.get_is_enabled():
                strategies_eval_class_instance.set_logger(
                    logging.getLogger(strategies_eval_class_instance.get_name()))

                strategies_eval_list.append(strategies_eval_class_instance)

        return strategies_eval_list

    @staticmethod
    def init_time_frames_from_strategies(config):
        time_frame_list = set()
        for strategies_eval_class in AdvancedManager.create_advanced_evaluator_types_list(StrategiesEvaluator, config):
            if strategies_eval_class.is_enabled(config, False):
                for time_frame in strategies_eval_class.get_required_time_frames(config):
                    time_frame_list.add(time_frame)
        time_frame_list = TimeFrameManager.sort_time_frames(time_frame_list)
        config[CONFIG_TIME_FRAME] = time_frame_list

    @staticmethod
    def get_relevant_evaluators_from_strategies(config):
        evaluator_list = set()
        for strategies_eval_class in AdvancedManager.create_advanced_evaluator_types_list(StrategiesEvaluator, config):
            if strategies_eval_class.is_enabled(config, False):
                required_evaluators = strategies_eval_class.get_required_evaluators(config)
                if required_evaluators == CONFIG_EVALUATORS_WILDCARD:
                    return CONFIG_EVALUATORS_WILDCARD
                else:
                    for evaluator in required_evaluators:
                        evaluator_list.add(evaluator)
        return evaluator_list

    @staticmethod
    def is_relevant_evaluator(evaluator_instance, relevant_evaluators):
        if evaluator_instance.get_is_enabled():
            if relevant_evaluators == CONFIG_EVALUATORS_WILDCARD or \
                    evaluator_instance.get_name() in relevant_evaluators:
                return True
            else:
                parent_classes_names = [e.get_name() for e in evaluator_instance.get_parent_evaluator_classes()]
                to_check_set = relevant_evaluators
                if not isinstance(relevant_evaluators, set):
                    to_check_set = set(relevant_evaluators)
                return not to_check_set.isdisjoint(parent_classes_names)
        return False

    @staticmethod
    def get_relevant_TAs_for_strategy(strategy, config):
        ta_classes_list = []
        relevant_evaluators = strategy.get_required_evaluators(config)
        for ta_eval_class in AdvancedManager.create_advanced_evaluator_types_list(TAEvaluator, config):
            ta_eval_class_instance = ta_eval_class()
            ta_eval_class_instance.set_config(config)
            if EvaluatorCreator.is_relevant_evaluator(ta_eval_class_instance, relevant_evaluators):
                ta_classes_list.append(ta_eval_class)
        return ta_classes_list
