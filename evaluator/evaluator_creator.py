#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger

from config import CONFIG_TIME_FRAME, CONFIG_EVALUATORS_WILDCARD
from evaluator.RealTime import RealTimeEvaluator, RealTimeExchangeEvaluator
from evaluator.Social import SocialEvaluator
from evaluator.Strategies import StrategiesEvaluator
from evaluator.TA import TAEvaluator
from tentacles_management.advanced_manager import AdvancedManager
from tools.time_frame_manager import TimeFrameManager
from services.Dispatchers.dispatcher_creator import DispatcherCreator


class EvaluatorCreator:

    LOGGER = None

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    def get_logger():
        if EvaluatorCreator.LOGGER is None:
            EvaluatorCreator.LOGGER = get_logger(EvaluatorCreator.get_name())
        return EvaluatorCreator.LOGGER

    @staticmethod
    def create_ta_eval_list(evaluator, relevant_evaluators):
        ta_eval_instance_list = []
        for ta_eval_class in AdvancedManager.create_advanced_evaluator_types_list(TAEvaluator, evaluator.get_config()):
            try:
                ta_eval_class_instance = ta_eval_class()
                ta_eval_class_instance.set_config(evaluator.config)
                if EvaluatorCreator.is_relevant_evaluator(ta_eval_class_instance, relevant_evaluators):
                    ta_eval_class_instance.set_logger(get_logger(ta_eval_class.get_name()))
                    ta_eval_class_instance.set_data(evaluator.data)
                    ta_eval_class_instance.set_symbol(evaluator.get_symbol())
                    ta_eval_instance_list.append(ta_eval_class_instance)
            except Exception as e:
                EvaluatorCreator.get_logger().error(f"Error when creating evaluator {ta_eval_class}: {e}")
                EvaluatorCreator.get_logger().exception(e)

        return ta_eval_instance_list

    @staticmethod
    def create_social_eval(config, symbol, dispatchers_list, relevant_evaluators):
        social_eval_list = []
        for social_eval_class in AdvancedManager.create_advanced_evaluator_types_list(SocialEvaluator, config):
            try:
                social_eval_class_instance = social_eval_class()
                social_eval_class_instance.set_config(config)
                if EvaluatorCreator.is_relevant_evaluator(social_eval_class_instance, relevant_evaluators):
                    is_evaluator_to_be_used = True
                    social_eval_class_instance.set_logger(get_logger(social_eval_class.get_name()))
                    social_eval_class_instance.set_symbol(symbol)
                    social_eval_class_instance.prepare()

                    is_dispatcher_client, is_evaluator_to_be_used = \
                        DispatcherCreator.bind_to_dispatcher_if_necessary(social_eval_class_instance,
                                                                          dispatchers_list,
                                                                          symbol,
                                                                          is_evaluator_to_be_used)
                    # register refreshing task if the evaluator is not managed by a dispatcher
                    if not is_dispatcher_client and \
                            is_evaluator_to_be_used and \
                            social_eval_class_instance.get_is_to_be_independently_tasked():
                        social_eval_class_instance.set_is_to_be_started_as_task(True)

                    if is_evaluator_to_be_used:
                        social_eval_list.append(social_eval_class_instance)
            except Exception as e:
                EvaluatorCreator.get_logger().error(f"Error when creating evaluator {social_eval_class}: {e}")
                EvaluatorCreator.get_logger().exception(e)

        return social_eval_list

    @staticmethod
    def instantiate_real_time_evaluator(real_time_eval_class, exchange, symbol):
        parent_classes = real_time_eval_class.get_parent_evaluator_classes()
        if RealTimeExchangeEvaluator in parent_classes:
            return real_time_eval_class(exchange, symbol)
        else:
            return real_time_eval_class(symbol)

    @staticmethod
    def create_real_time_ta_evals(config, exchange_inst, symbol, relevant_evaluators, dispatchers_list):
        real_time_ta_eval_list = []
        for real_time_eval_class in AdvancedManager.create_advanced_evaluator_types_list(RealTimeEvaluator, config):
            try:
                real_time_eval_class_instance = EvaluatorCreator.instantiate_real_time_evaluator(real_time_eval_class,
                                                                                                 exchange_inst, symbol)
                real_time_eval_class_instance.set_config(config)
                if EvaluatorCreator.is_relevant_evaluator(real_time_eval_class_instance, relevant_evaluators):
                    real_time_eval_class_instance.set_logger(get_logger(real_time_eval_class.get_name()))

                    is_dispatcher_client, is_evaluator_to_be_used = \
                        DispatcherCreator.bind_to_dispatcher_if_necessary(real_time_eval_class_instance,
                                                                          dispatchers_list, symbol, True)

                    # register refreshing task
                    if not is_dispatcher_client:
                        real_time_eval_class_instance.set_is_to_be_started_as_task(True)

                    if is_evaluator_to_be_used:
                        real_time_ta_eval_list.append(real_time_eval_class_instance)
            except Exception as e:
                EvaluatorCreator.get_logger().error(f"Error when creating evaluator {real_time_eval_class}: {e}")
                EvaluatorCreator.get_logger().exception(e)

        return real_time_ta_eval_list

    @staticmethod
    def create_social_not_tasked_list(social_eval_list):
        return [
            social_eval
            for social_eval in social_eval_list
            if not social_eval.get_is_to_be_started_as_task()
        ]

    @staticmethod
    def create_strategies_eval_list(config):
        strategies_eval_list = []
        for strategies_eval_class in AdvancedManager.create_advanced_evaluator_types_list(StrategiesEvaluator, config):
            try:
                strategies_eval_class_instance = strategies_eval_class()
                strategies_eval_class_instance.set_config(config)
                if strategies_eval_class_instance.get_is_enabled():
                    strategies_eval_class_instance.set_logger(
                        get_logger(strategies_eval_class_instance.get_name()))

                    strategies_eval_list.append(strategies_eval_class_instance)
            except Exception as e:
                EvaluatorCreator.get_logger().error(f"Error when creating strategy {strategies_eval_class}: {e}")
                EvaluatorCreator.get_logger().exception(e)

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
