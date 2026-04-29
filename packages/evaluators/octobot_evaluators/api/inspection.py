#  Drakkar-Software OctoBot-Evaluators
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
import octobot_commons.constants as common_constants
import octobot_commons.tentacles_management as tentacles_management

import octobot_evaluators.evaluators as evaluator


def is_relevant_evaluator(evaluator_instance, relevant_evaluators, use_relevant_evaluators_only=False) -> bool:
    if evaluator_instance.enabled or use_relevant_evaluators_only:
        if relevant_evaluators == common_constants.CONFIG_WILDCARD or \
                evaluator_instance.get_name() in relevant_evaluators:
            return True
        else:
            parent_classes_names = [e.get_name() for e in evaluator_instance.get_parent_evaluator_classes()]
            to_check_set = relevant_evaluators
            if not isinstance(relevant_evaluators, set):
                to_check_set = set(relevant_evaluators)
            return not to_check_set.isdisjoint(parent_classes_names)
    return False


def get_relevant_TAs_for_strategy(strategy, tentacles_setup_config) -> list:
    ta_classes_list = []
    relevant_evaluators = strategy.get_required_evaluators(tentacles_setup_config)
    for ta_eval_class in tentacles_management.get_all_classes_from_parent(evaluator.TAEvaluator):
        ta_eval_class_instance = ta_eval_class(tentacles_setup_config)
        # use ony relevant_evaluators given by the strategy
        if common_constants.CONFIG_WILDCARD in relevant_evaluators or \
                is_relevant_evaluator(ta_eval_class_instance, relevant_evaluators, use_relevant_evaluators_only=True):
            ta_classes_list.append(ta_eval_class)
    return ta_classes_list
