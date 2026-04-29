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
import async_channel.util as channel_util

import octobot_tentacles_manager.api as api

import octobot_commons.constants as common_constants
import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.time_frame_manager as time_frame_manager

import octobot_evaluators.evaluators.channel as evaluator_channels
import octobot_evaluators.constants as constants
import octobot_evaluators.evaluators as evaluator
import octobot_evaluators.util as util


def init_time_frames_from_strategies(config, tentacles_setup_config, config_by_strategy=None) -> None:
    config[common_constants.CONFIG_TIME_FRAME] = get_time_frames_from_strategies(
        config, tentacles_setup_config, config_by_strategy=config_by_strategy
    )


def get_time_frames_from_strategies(config, tentacles_setup_config, config_by_strategy=None) -> list:
    config_by_strategy = config_by_strategy or {}
    time_frame_list = set(
        time_frame
        for strategies_eval_class in get_activated_strategies_classes(tentacles_setup_config)
        for time_frame in get_time_frames_from_strategy(
            strategies_eval_class, config, tentacles_setup_config,
            config_by_strategy.get(strategies_eval_class.get_name())
        )
    )
    return time_frame_manager.sort_time_frames(list(time_frame_list))


def get_time_frames_from_strategy(strategy_class, config, tentacles_setup_config, strategy_config=None) -> list:
    return strategy_class.get_required_time_frames(config, tentacles_setup_config, strategy_config=strategy_config)


def init_required_candles_count_from_evaluators_and_strategies(config, tentacles_setup_config) -> None:
    candles_counts = [util.get_required_candles_count(tentacle_class, tentacles_setup_config)
                      for tentacle_class in get_activated_evaluators(tentacles_setup_config)]
    config[common_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT] = max(candles_counts) if candles_counts \
        else common_constants.DEFAULT_IGNORED_VALUE


def get_activated_evaluators(tentacles_setup_config):
    return get_activated_TA_evaluators_classes(tentacles_setup_config) + \
        get_activated_scripted_evaluators_classes(tentacles_setup_config) + \
        get_activated_real_time_evaluators_classes(tentacles_setup_config) + \
        get_activated_social_evaluators_classes(tentacles_setup_config) + \
        get_activated_strategies_classes(tentacles_setup_config)


def get_activated_strategies_classes(tentacles_setup_config):
    return _get_activated_classes(tentacles_setup_config, evaluator.StrategyEvaluator)


def get_activated_TA_evaluators_classes(tentacles_setup_config):
    return _get_activated_classes(tentacles_setup_config, evaluator.TAEvaluator)


def get_activated_scripted_evaluators_classes(tentacles_setup_config):
    return _get_activated_classes(tentacles_setup_config, evaluator.ScriptedEvaluator)


def get_activated_real_time_evaluators_classes(tentacles_setup_config):
    return _get_activated_classes(tentacles_setup_config, evaluator.RealTimeEvaluator)


def get_activated_social_evaluators_classes(tentacles_setup_config):
    return _get_activated_classes(tentacles_setup_config, evaluator.SocialEvaluator)


def _get_activated_classes(tentacles_setup_config, parent_class):
    return [
        child_class
        for child_class in tentacles_management.get_all_classes_from_parent(parent_class)
        if api.is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config, child_class.get_name())
    ]


async def create_evaluator_channels(matrix_id: str, is_backtesting: bool = False) -> None:
    await channel_util.create_all_subclasses_channel(evaluator_channels.EvaluatorChannel,
                                                     evaluator_channels.set_chan,
                                                     is_synchronized=is_backtesting, matrix_id=matrix_id)


def del_evaluator_channels(matrix_id: str) -> None:
    evaluator_channels.del_chan(constants.MATRIX_CHANNEL, matrix_id)
    evaluator_channels.del_chan(constants.EVALUATORS_CHANNEL, matrix_id)


def matrix_channel_exists(matrix_id: str) -> bool:
    try:
        evaluator_channels.get_chan(constants.MATRIX_CHANNEL, matrix_id)
        return True
    except KeyError:
        return False
