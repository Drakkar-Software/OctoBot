#  Drakkar-Software OctoBot-Interfaces
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

import octobot.api as octobot_api
import octobot.constants as octobot_constants
import octobot_commons.logging as bot_logging
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.api as evaluators_api
import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface as web_interface_root
import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Evaluator.Strategies as TentaclesStrategies

LOGGER = bot_logging.get_logger(__name__)


def get_strategies_list(trading_mode):
    try:
        return trading_mode.get_required_strategies_names_and_count(interfaces_util.get_startup_tentacles_config())[0]
    except Exception:
        return []


def get_time_frames_list(strategy_name):
    if strategy_name:
        strategy_class = tentacles_management.get_class_from_string(strategy_name, evaluators.StrategyEvaluator,
                                                                    TentaclesStrategies,
                                                                    tentacles_management.evaluator_parent_inspection)
        return [tf.value for tf in strategy_class.get_required_time_frames(
            interfaces_util.get_global_config(),
            interfaces_util.get_bot_api().get_tentacles_setup_config())]
    else:
        return []


def get_evaluators_list(strategy_name):
    if strategy_name:
        strategy_class = tentacles_management.get_class_from_string(strategy_name, evaluators.StrategyEvaluator,
                                                                    TentaclesStrategies,
                                                                    tentacles_management.evaluator_parent_inspection)
        found_evaluators = evaluators_api.get_relevant_TAs_for_strategy(
            strategy_class, interfaces_util.get_bot_api().get_tentacles_setup_config())
        return set(evaluator.get_name() for evaluator in found_evaluators)
    else:
        return []


def get_risks_list():
    return [i / 10 for i in range(10, 0, -1)]


def cancel_optimizer():
    tools = web_interface_root.WebInterface.tools
    optimizer = tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer is None:
        return False, "No optimizer is running"
    octobot_api.cancel_strategy_optimizer(optimizer)
    return True, "Optimizer is being cancelled"


def start_optimizer(strategy, time_frames, evaluators, risks):
    if not octobot_constants.ENABLE_BACKTESTING:
        return False, "Backtesting is disabled"
    try:
        tools = web_interface_root.WebInterface.tools
        optimizer = tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
        if optimizer is not None and octobot_api.is_optimizer_computing(optimizer):
            return False, "Optimizer already running"
        independent_backtesting = tools[constants.BOT_TOOLS_BACKTESTING]
        if independent_backtesting and octobot_api.is_independent_backtesting_in_progress(independent_backtesting):
            return False, "A backtesting is already running"
        formatted_time_frames = time_frame_manager.parse_time_frames(time_frames)
        float_risks = [float(risk) for risk in risks]
        temp_independent_backtesting = octobot_api.create_independent_backtesting(
            interfaces_util.get_global_config(), None, [])
        optimizer_config = interfaces_util.run_in_bot_async_executor(
            octobot_api.initialize_independent_backtesting_config(temp_independent_backtesting)
        )
        optimizer = octobot_api.create_strategy_optimizer(optimizer_config,
                                                          interfaces_util.get_bot_api().get_edited_tentacles_config(),
                                                          strategy)
        tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER] = optimizer
        thread = threading.Thread(target=octobot_api.find_optimal_configuration,
                                  args=(optimizer, evaluators, formatted_time_frames, float_risks),
                                  name=f"{optimizer.get_name()}-WebInterface-runner")
        thread.start()
        return True, "Optimizer started"
    except Exception as e:
        LOGGER.exception(e, True, f"Error when starting optimizer: {e}")
        raise e


def get_optimizer_results():
    optimizer = web_interface_root.WebInterface.tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer:
        results = octobot_api.get_optimizer_results(optimizer)
        return [result.get_result_dict(i) for i, result in enumerate(results)]
    else:
        return []


def get_optimizer_report():
    if get_optimizer_status()[0] == "finished":
        optimizer = web_interface_root.WebInterface.tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
        return octobot_api.get_optimizer_report(optimizer)
    else:
        return []


def get_current_run_params():
    params = {
        "strategy_name": [],
        "time_frames": [],
        "evaluators": [],
        "risks": [],
        "trading_mode": []
    }
    if web_interface_root.WebInterface.tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]:
        optimizer = web_interface_root.WebInterface.tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
        params = {
            "strategy_name": [octobot_api.get_optimizer_strategy(optimizer).get_name()],
            "time_frames": [tf.value for tf in octobot_api.get_optimizer_all_time_frames(optimizer)],
            "evaluators": octobot_api.get_optimizer_all_TAs(optimizer),
            "risks": octobot_api.get_optimizer_all_risks(optimizer),
            "trading_mode": [octobot_api.get_optimizer_trading_mode(optimizer)]
        }
    return params


def get_optimizer_status():
    optimizer = web_interface_root.WebInterface.tools[constants.BOT_TOOLS_STRATEGY_OPTIMIZER]
    if optimizer:
        if octobot_api.is_optimizer_computing(optimizer):
            overall_progress, remaining_time =\
                interfaces_util.run_in_bot_async_executor(octobot_api.get_optimizer_overall_progress(optimizer))
            return "computing", octobot_api.get_optimizer_current_test_suite_progress(optimizer), \
                   overall_progress, remaining_time, \
                   octobot_api.get_optimizer_errors_description(optimizer)
        else:
            status = "finished" if octobot_api.is_optimizer_finished(optimizer) else "starting"
            return status, 100, 100, 0, octobot_api.get_optimizer_errors_description(optimizer)
    else:
        return "not started", 0, 0, 0, None
