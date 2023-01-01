#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import pytest_asyncio

import octobot.strategy_optimizer as strategy_optimizer
import octobot_trading.api as trading_api
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_evaluators.constants as evaluators_constants

import tentacles.Evaluator.Strategies as Strategies
import tentacles.Evaluator.TA as Evaluator
import tentacles.Trading.Mode as Mode


@pytest_asyncio.fixture
async def optimizer_inputs():
    tentacles_setup_config = tentacles_manager_api.create_tentacles_setup_config_with_tentacles(
        Mode.DailyTradingMode,
        Strategies.SimpleStrategyEvaluator,
        Evaluator.RSIMomentumEvaluator,
        Evaluator.DoubleMovingAverageTrendEvaluator
    )
    trading_mode = trading_api.get_activated_trading_mode(tentacles_setup_config)
    return tentacles_setup_config, trading_mode


def _get_optimizer_user_input_config(tentacle, user_input_name, enabled, value):
    return {
        get_ui_identifier(tentacle, user_input_name): {
            "enabled": enabled,
            "tentacle": tentacle.get_name(),
            "user_input": user_input_name,
            "value": value
        }
    }


def get_ui_identifier(tentacle, user_input_name):
    return f"{tentacle.get_name()}-{user_input_name}"


def _get_mocked_ui_config():
    return {
        key: val
        for element in [
            _get_optimizer_user_input_config(
                Evaluator.RSIMomentumEvaluator, "period_length", True,
                {
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MAX: 15,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MIN: 3,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_STEP: 2
                }
            ),
            _get_optimizer_user_input_config(
                Evaluator.RSIMomentumEvaluator, "constrained_risk", True,
                {
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MAX: 2,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MIN: 1,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_STEP: 1
                }
            ),
            _get_optimizer_user_input_config(
                Strategies.SimpleStrategyEvaluator, commons_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT, False,
                {
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MAX: 0,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_MIN: 0,
                    strategy_optimizer.StrategyDesignOptimizer.CONFIG_STEP: 1
                }
            ),
            _get_optimizer_user_input_config(
                Strategies.SimpleStrategyEvaluator, evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME, True,
                [
                    commons_enums.TimeFrames.FIVE_MINUTES.value,
                    commons_enums.TimeFrames.ONE_HOUR.value,
                    commons_enums.TimeFrames.ONE_DAY.value,
                ]
            ),
            _get_optimizer_user_input_config(
                Strategies.SimpleStrategyEvaluator, Strategies.SimpleStrategyEvaluator.RE_EVAL_TA_ON_RT_OR_SOCIAL, True,
                [
                    False
                ]
            ),
        ]
        for key, val in element.items()
    }


def _get_filter_setting_content(role, value):
    return {
        strategy_optimizer.StrategyDesignOptimizer.CONFIG_ROLE: role,
        strategy_optimizer.StrategyDesignOptimizer.CONFIG_VALUE: value,
    }


def _get_filter_setting(left_value, right_value, flat_value, operator):
    return {
        "user_input_left_operand": _get_filter_setting_content(
            "user_input_left_operand",
            left_value
        ),
        "user_input_right_operand": _get_filter_setting_content(
            "user_input_right_operand",
            right_value
        ),
        "text_right_operand": _get_filter_setting_content(
            "text_right_operand",
            flat_value

        ),
        "operator": _get_filter_setting_content(
            strategy_optimizer.OptimizerFilter.OPERATOR_KEY,
            operator.value
        ),
    }


def _get_mocked_filters_settings():
    return [
        _get_filter_setting(get_ui_identifier(Evaluator.RSIMomentumEvaluator, "period_length"), "null", 5,
                            commons_enums.LogicalOperators.LOWER_THAN),
        _get_filter_setting(get_ui_identifier(Evaluator.RSIMomentumEvaluator, "period_length"), "null", 15,
                            commons_enums.LogicalOperators.HIGHER_OR_EQUAL_TO),
    ]


MOCKED_OPTIMIZER_CONFIG = {
    strategy_optimizer.StrategyDesignOptimizer.CONFIG_FILTER_SETTINGS: _get_mocked_filters_settings(),
    strategy_optimizer.StrategyDesignOptimizer.CONFIG_USER_INPUTS: _get_mocked_ui_config(),
}


def _get_mocked_run_ui(ui_name, tentacle, value):
    return {
        strategy_optimizer.StrategyDesignOptimizer.CONFIG_USER_INPUT: ui_name,
        strategy_optimizer.StrategyDesignOptimizer.CONFIG_TENTACLE: [tentacle.get_name()],
        strategy_optimizer.StrategyDesignOptimizer.CONFIG_VALUE: value
    }


def _get_mocked_run(period_length, constrained_risk, time_frame):
    return (
        _get_mocked_run_ui("period_length", Evaluator.RSIMomentumEvaluator, period_length),
        _get_mocked_run_ui("constrained_risk", Evaluator.RSIMomentumEvaluator, constrained_risk),
        _get_mocked_run_ui(evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME,
                           Strategies.SimpleStrategyEvaluator,
                           [time_frame.value]),
        _get_mocked_run_ui(Strategies.SimpleStrategyEvaluator.RE_EVAL_TA_ON_RT_OR_SOCIAL,
                           Strategies.SimpleStrategyEvaluator, False),
    )


MOCKED_RUNS = [
    _get_mocked_run(period_length_val, constrained_risk_val, time_frame_val)
    for period_length_val in (5, 7, 9, 11, 13)
    for constrained_risk_val in (1, 2)
    for time_frame_val in (commons_enums.TimeFrames.FIVE_MINUTES,
                           commons_enums.TimeFrames.ONE_HOUR,
                           commons_enums.TimeFrames.ONE_DAY)
]


EXPECTED_RUNS_FROM_MOCK = {
    index + 6: val  # index + 6 as the first 5 runs have been filtered
    for index, val in enumerate(MOCKED_RUNS)
}
