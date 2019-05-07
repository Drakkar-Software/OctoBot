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

import threading


from interfaces import get_bot
from tentacles_management.advanced_manager import AdvancedManager
from evaluator.Strategies.strategies_evaluator import StrategiesEvaluator
from evaluator.evaluator_creator import EvaluatorCreator
from evaluator import Strategies
from tentacles_management.class_inspector import get_class_from_string, evaluator_parent_inspection
from tools.time_frame_manager import TimeFrameManager
from config import BOT_TOOLS_STRATEGY_OPTIMIZER, BOT_TOOLS_BACKTESTING
from backtesting.strategy_optimizer.strategy_optimizer import StrategyOptimizer


def get_strategies_list():
    try:
        config = get_bot().get_config()
        classes = AdvancedManager.get_all_classes(StrategiesEvaluator, config)
        return set(strategy.get_name() for strategy in classes)
    except Exception:
        return []


def get_time_frames_list(strategy_name):
    if strategy_name:
        strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                               Strategies, evaluator_parent_inspection)
        return [tf.value for tf in strategy_class.get_required_time_frames(get_bot().get_config())]
    else:
        return []


def get_evaluators_list(strategy_name):
    if strategy_name:
        strategy_class = get_class_from_string(strategy_name, StrategiesEvaluator,
                                               Strategies, evaluator_parent_inspection)
        evaluators = EvaluatorCreator.get_relevant_TAs_for_strategy(strategy_class, get_bot().get_config())
        return set(evaluator.get_name() for evaluator in evaluators)
    else:
        return []


def get_risks_list():
    return [i/10 for i in range(10, 0, -1)]


def get_current_strategy():
    try:
        first_symbol_evaluator = next(iter(get_bot().get_symbol_evaluator_list().values()))
        first_exchange = next(iter(get_bot().get_exchanges_list().values()))
        return first_symbol_evaluator.get_strategies_eval_list(first_exchange)[0].get_name()
    except Exception:
        strategy_list = get_strategies_list()
        return next(iter(strategy_list)) if strategy_list else ""


def start_optimizer(strategy, time_frames, evaluators, risks):
    tools = get_bot().get_tools()
    tools[BOT_TOOLS_STRATEGY_OPTIMIZER] = StrategyOptimizer(get_bot().get_config(), strategy)
    optimizer = tools[BOT_TOOLS_STRATEGY_OPTIMIZER]
    backtester = tools[BOT_TOOLS_BACKTESTING]
    if optimizer.get_is_computing():
        return False, "Optimizer already running"
    elif backtester and backtester.get_is_computing():
        return False, "A backtesting is already running"
    else:
        formatted_time_frames = TimeFrameManager.parse_time_frames(time_frames)
        float_risks = [float(risk) for risk in risks]
        thread = threading.Thread(target=optimizer.find_optimal_configuration, args=(evaluators,
                                                                                     formatted_time_frames,
                                                                                     float_risks))
        thread.start()
        return True, "Optimizer started"


def get_optimizer_results():
    optimizer = get_bot().get_tools()[BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer:
        results = optimizer.get_results()
        return [result.get_result_dict(i) for i, result in enumerate(results)]
    else:
        return []


def get_optimizer_report():
    if get_optimizer_status()[0] == "finished":
        optimizer = get_bot().get_tools()[BOT_TOOLS_STRATEGY_OPTIMIZER]
        return optimizer.get_report()
    else:
        return []


def get_current_run_params():
    tools = get_bot().get_tools()
    params = {
        "strategy_name": [],
        "time_frames": [],
        "evaluators": [],
        "risks": [],
        "trading_mode": []
    }
    if tools[BOT_TOOLS_STRATEGY_OPTIMIZER]:
        optimizer = tools[BOT_TOOLS_STRATEGY_OPTIMIZER]
        params = {
            "strategy_name": [optimizer.strategy_class.get_name()],
            "time_frames": [tf.value for tf in optimizer.all_time_frames],
            "evaluators": optimizer.all_TAs,
            "risks": optimizer.risks,
            "trading_mode": [optimizer.trading_mode]
        }
    return params


def get_trading_mode():
    return get_bot().get_trading_mode().get_name()


def get_optimizer_status():
    tools = get_bot().get_tools()
    if tools[BOT_TOOLS_STRATEGY_OPTIMIZER]:
        optimizer = tools[BOT_TOOLS_STRATEGY_OPTIMIZER]
        if optimizer.get_is_computing():
            return "computing", optimizer.get_current_test_suite_progress(), optimizer.get_overall_progress(), \
                   optimizer.get_errors_description()
        else:
            return "finished", 100, 100, optimizer.get_errors_description()
    else:
        return "not started", 0, 0, None
