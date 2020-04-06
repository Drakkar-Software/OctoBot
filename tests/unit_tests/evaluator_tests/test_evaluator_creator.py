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


from evaluator.evaluator_creator import EvaluatorCreator
from evaluator.Strategies import StrategiesEvaluator
from tests.test_utils.config import load_test_config
from octobot_commons.tentacles_management.advanced_manager import AdvancedManager
from config import TimeFrames, CONFIG_EVALUATORS_WILDCARD
from evaluator.evaluator import Evaluator
from evaluator.TA import TAEvaluator
from evaluator.Social import SocialEvaluator


def _get_tools():
    config = load_test_config()
    AdvancedManager.create_class_list(config)
    evaluator = Evaluator()
    evaluator.set_config(config)
    evaluator.set_symbol("BTC/USDT")
    evaluator.set_time_frame(TimeFrames.ONE_HOUR)
    return evaluator, config


def _assert_created_instances(instances_list, super_class, config):
    class_list = [instance.__class__ for instance in instances_list]
    for eval_class in AdvancedManager.create_advanced_evaluator_types_list(super_class, config):
        eval_instance = eval_class()
        eval_instance.set_config(config)
        if eval_instance.get_is_enabled():
            assert eval_class in class_list


def test_create_ta_eval_list():
    evaluator, config = _get_tools()
    ta_list = EvaluatorCreator.create_ta_eval_list(evaluator, CONFIG_EVALUATORS_WILDCARD)
    _assert_created_instances(ta_list, TAEvaluator, config)


def test_create_social_eval_list():
    evaluator, config = _get_tools()
    so_list = EvaluatorCreator.create_social_eval(config, evaluator.symbol, [], CONFIG_EVALUATORS_WILDCARD)
    _assert_created_instances(so_list, SocialEvaluator, config)


def test_create_social_not_tasked_list():
    evaluator, config = _get_tools()
    so_list = EvaluatorCreator.create_social_eval(config, evaluator.symbol, [], CONFIG_EVALUATORS_WILDCARD)
    not_tasked_so_list = EvaluatorCreator.create_social_not_tasked_list(so_list)
    for evalator in not_tasked_so_list:
        assert not evalator.is_to_be_independently_tasked


def test_create_strategies_eval_list():
    evaluator, config = _get_tools()
    strat_list = EvaluatorCreator.create_strategies_eval_list(config)
    _assert_created_instances(strat_list, StrategiesEvaluator, config)


# not tested for now
# def test_create_real_time_ta_evals():
#     evaluator, config = _get_tools()
#     ta_list = EvaluatorCreator.create_real_time_ta_evals(config, evaluator.exchange,
#                                                          evaluator.symbol, CONFIG_EVALUATORS_WILDCARD)
#     _assert_created_instances(ta_list, RealTimeEvaluator, config)
