#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import pytest
import pytest_asyncio
import mock

import octobot.api as bot_module_api
import octobot.strategy_optimizer as strategy_optimizer
import octobot_trading.api as trading_api
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_evaluators.constants as evaluators_constants

import tentacles.Evaluator.Strategies as Strategies
import tentacles.Evaluator.TA as Evaluator
import tentacles.Trading.Mode as Mode

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


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


async def test_generate_and_save_strategy_optimizer_runs(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        commons_enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
    })
    with mock.patch.object(databases.TinyDBAdaptor, "create_identifier", mock.AsyncMock()) as create_identifier_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_save_run_schedule", mock.AsyncMock()) as \
                    _save_run_schedule_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "shuffle_and_select_runs", mock.Mock(
                side_effect=lambda *args, **_: args[0]
            )) as shuffle_and_select_runs_mock:
        assert await bot_module_api.generate_and_save_strategy_optimizer_runs(
            trading_mode,
            tentacles_setup_config,
            optimizer_settings
        ) == EXPECTED_RUNS_FROM_MOCK
        create_identifier_mock.assert_called_once()
        shuffle_and_select_runs_mock.assert_called_once()
        _save_run_schedule_mock.assert_awaited_once_with(EXPECTED_RUNS_FROM_MOCK)


async def test_resume_unknown_mode(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        commons_enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
        commons_enums.OptimizerConfig.OPTIMIZER_IDS.value: [1],
        commons_enums.OptimizerConfig.MODE.value: "plop",
    })
    with mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_get_total_nb_runs",
                          mock.AsyncMock(return_value=5)) as _get_total_nb_runs_mock:
        optimizer = bot_module_api.create_design_strategy_optimizer(
            trading_mode,
            optimizer_settings,
            None,
            tentacles_setup_config,
        )
        with pytest.raises(NotImplementedError):
            await optimizer.resume(optimizer_settings)
        _get_total_nb_runs_mock.assert_called_once_with(optimizer_settings.optimizer_ids)


async def test_resume_normal_mode(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        commons_enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
        commons_enums.OptimizerConfig.DATA_FILES.value: ["data_file"],
        commons_enums.OptimizerConfig.OPTIMIZER_IDS.value: [1],
        commons_enums.OptimizerConfig.RANDOMLY_CHOSE_RUNS.value: False,
        commons_enums.OptimizerConfig.START_TIMESTAMP.value: 1661990400,
        commons_enums.OptimizerConfig.END_TIMESTAMP.value: 1667347200,
        commons_enums.OptimizerConfig.IDLE_CORES.value: 5,
        commons_enums.OptimizerConfig.NOTIFY_WHEN_COMPLETE.value: True,
        commons_enums.OptimizerConfig.MODE.value: commons_enums.OptimizerModes.NORMAL.value,
        commons_enums.OptimizerConfig.EMPTY_THE_QUEUE.value: False,
    })
    with mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_get_total_nb_runs",
                          mock.AsyncMock(return_value=5)) as _get_total_nb_runs_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "multi_processed_optimize",
                              mock.AsyncMock(return_value=True)) as multi_processed_optimize_mock:
        optimizer = bot_module_api.create_design_strategy_optimizer(
            trading_mode,
            optimizer_settings,
            None,
            tentacles_setup_config,
        )
        assert await optimizer.resume(optimizer_settings) is True
        _get_total_nb_runs_mock.assert_called_once_with(optimizer_settings.optimizer_ids)
        multi_processed_optimize_mock.assert_awaited_once_with(optimizer_settings)


async def test_resume_genetic_mode(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        commons_enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
        commons_enums.OptimizerConfig.DATA_FILES.value: ["data_file"],
        commons_enums.OptimizerConfig.OPTIMIZER_IDS.value: [1],
        commons_enums.OptimizerConfig.RANDOMLY_CHOSE_RUNS.value: False,
        commons_enums.OptimizerConfig.START_TIMESTAMP.value: 1661990400,
        commons_enums.OptimizerConfig.END_TIMESTAMP.value: 1667347200,
        commons_enums.OptimizerConfig.IDLE_CORES.value: 0,
        commons_enums.OptimizerConfig.NOTIFY_WHEN_COMPLETE.value: True,
        commons_enums.OptimizerConfig.MODE.value: commons_enums.OptimizerModes.GENETIC.value,
        commons_enums.OptimizerConfig.EMPTY_THE_QUEUE.value: False,
        commons_enums.OptimizerConfig.DEFAULT_GENERATIONS_COUNT.value: 10,
        commons_enums.OptimizerConfig.STAY_WITHIN_BOUNDARIES.value: False,
        commons_enums.OptimizerConfig.INITIAL_GENERATION_COUNT.value: 8,
        commons_enums.OptimizerConfig.DEFAULT_RUN_PER_GENERATION.value: 8,
        commons_enums.OptimizerConfig.TARGET_FITNESS_SCORE.value: None,
    })
    with mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_get_total_nb_runs",
                          mock.AsyncMock(return_value=5)) as _get_total_nb_runs_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "multi_processed_optimize",
                              mock.AsyncMock(return_value=True)) as multi_processed_optimize_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_generate_first_generation_run_data",
                              mock.AsyncMock(return_value=EXPECTED_RUNS_FROM_MOCK)) as \
                    _generate_first_generation_run_data_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_get_all_finished_run_results",
                              mock.AsyncMock(return_value=RUNS_RESULTS_FROM_MOCK)) as \
                    _get_all_finished_run_results_mock, \
            mock.patch.object(strategy_optimizer.StrategyDesignOptimizer, "_send_optimizer_finished_notification",
                              mock.AsyncMock()) as \
                    _send_optimizer_finished_notification_mock:
        optimizer = bot_module_api.create_design_strategy_optimizer(
            trading_mode,
            optimizer_settings,
            None,
            tentacles_setup_config,
        )
        assert await optimizer.resume(optimizer_settings) is True
        _get_total_nb_runs_mock.assert_called_once_with(optimizer_settings.optimizer_ids)
        _generate_first_generation_run_data_mock.assert_awaited_once()
        _send_optimizer_finished_notification_mock.assert_awaited_once()
        assert optimizer_settings.generations_count > multi_processed_optimize_mock.call_count > 0


def _get_ui_identifier(tentacle, user_input_name):
    return f"{tentacle.get_name()}-{user_input_name}"


def _get_optimizer_user_input_config(tentacle, user_input_name, enabled, value):
    return {
        _get_ui_identifier(tentacle, user_input_name): {
            "enabled": enabled,
            "tentacle": tentacle.get_name(),
            "user_input": user_input_name,
            "value": value
        }
    }


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
        _get_filter_setting(_get_ui_identifier(Evaluator.RSIMomentumEvaluator, "period_length"), "null", 5,
                            commons_enums.LogicalOperators.LOWER_THAN),
        _get_filter_setting(_get_ui_identifier(Evaluator.RSIMomentumEvaluator, "period_length"), "null", 15,
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


def _get_mocked_run(period_length, time_frame):
    return (
        _get_mocked_run_ui("period_length", Evaluator.RSIMomentumEvaluator, period_length),
        _get_mocked_run_ui(evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME,
                           Strategies.SimpleStrategyEvaluator,
                           [time_frame.value]),
        _get_mocked_run_ui(Strategies.SimpleStrategyEvaluator.RE_EVAL_TA_ON_RT_OR_SOCIAL,
                           Strategies.SimpleStrategyEvaluator, False),
    )


MOCKED_RUNS = [
    _get_mocked_run(period_length_val, time_frame_val)
    for period_length_val in (5, 7, 9, 11, 13)
    for time_frame_val in (commons_enums.TimeFrames.FIVE_MINUTES,
                           commons_enums.TimeFrames.ONE_HOUR,
                           commons_enums.TimeFrames.ONE_DAY)
]

EXPECTED_RUNS_FROM_MOCK = {
    index + 3: val  # index + 3 as the first 2 runs have been filtered
    for index, val in enumerate(MOCKED_RUNS)
}


def _get_mocked_run_result(period_length_val, time_frame_val):
    gains = period_length_val * commons_enums.TimeFramesMinutes[time_frame_val]
    r2 = period_length_val / commons_enums.TimeFramesMinutes[time_frame_val]
    trades = commons_enums.TimeFramesMinutes[time_frame_val]
    return {
        commons_enums.BacktestingMetadata.PERCENT_GAINS.value: gains,
        commons_enums.BacktestingMetadata.COEFFICIENT_OF_DETERMINATION_MAX_BALANCE.value: r2,
        commons_enums.BacktestingMetadata.TRADES.value: trades,
        commons_enums.BacktestingMetadata.USER_INPUTS.value: {
            Strategies.SimpleStrategyEvaluator.get_name(): {
                evaluators_constants.STRATEGIES_REQUIRED_TIME_FRAME: [time_frame_val.value],
                Strategies.SimpleStrategyEvaluator.RE_EVAL_TA_ON_RT_OR_SOCIAL: False,
            },
            Evaluator.RSIMomentumEvaluator.get_name(): {
                "period_length": period_length_val,
            }
        }
    }


RUNS_RESULTS_FROM_MOCK = [
    _get_mocked_run_result(period_length_val, time_frame_val)
    for period_length_val in (5, 7, 9, 11, 13)
    for time_frame_val in (commons_enums.TimeFrames.FIVE_MINUTES,
                           commons_enums.TimeFrames.ONE_HOUR,
                           commons_enums.TimeFrames.ONE_DAY)
]
