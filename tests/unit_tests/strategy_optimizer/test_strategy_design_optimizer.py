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
import math

import pytest
import pytest_asyncio
import mock

import octobot.api as bot_module_api
import octobot.enums as enums
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

from tests.unit_tests.strategy_optimizer import optimizer_inputs, MOCKED_OPTIMIZER_CONFIG, EXPECTED_RUNS_FROM_MOCK

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_generate_and_save_strategy_optimizer_runs(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
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
        enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
        enums.OptimizerConfig.OPTIMIZER_IDS.value: [1],
        enums.OptimizerConfig.MODE.value: "plop",
    })
    optimizer = bot_module_api.create_design_strategy_optimizer(
        trading_mode,
        optimizer_settings,
        None,
        tentacles_setup_config,
    )
    with mock.patch.object(optimizer, "_get_total_nb_runs",
                           mock.AsyncMock(return_value=5)) as _get_total_nb_runs_mock:
        with pytest.raises(NotImplementedError):
            await optimizer.resume(optimizer_settings)
        _get_total_nb_runs_mock.assert_awaited_once_with(optimizer_settings.optimizer_ids)


async def test_resume_normal_mode(optimizer_inputs):
    tentacles_setup_config, trading_mode = optimizer_inputs
    optimizer_settings = bot_module_api.create_strategy_optimizer_settings({
        enums.OptimizerConfig.OPTIMIZER_CONFIG.value: MOCKED_OPTIMIZER_CONFIG,
        enums.OptimizerConfig.DATA_FILES.value: ["data_file"],
        enums.OptimizerConfig.OPTIMIZER_IDS.value: [1],
        enums.OptimizerConfig.RANDOMLY_CHOSE_RUNS.value: False,
        enums.OptimizerConfig.START_TIMESTAMP.value: 1661990400,
        enums.OptimizerConfig.END_TIMESTAMP.value: 1667347200,
        enums.OptimizerConfig.IDLE_CORES.value: 5,
        enums.OptimizerConfig.NOTIFY_WHEN_COMPLETE.value: True,
        enums.OptimizerConfig.MODE.value: enums.OptimizerModes.NORMAL.value,
        enums.OptimizerConfig.EMPTY_THE_QUEUE.value: False,
    })
    optimizer = bot_module_api.create_design_strategy_optimizer(
        trading_mode,
        optimizer_settings,
        None,
        tentacles_setup_config,
    )
    with mock.patch.object(optimizer, "_get_total_nb_runs",
                           mock.AsyncMock(return_value=5)) as _get_total_nb_runs_mock, \
            mock.patch.object(optimizer, "multi_processed_optimize",
                              mock.AsyncMock(return_value=True)) as multi_processed_optimize_mock:
        assert await optimizer.resume(optimizer_settings) is True
        _get_total_nb_runs_mock.assert_called_once_with(optimizer_settings.optimizer_ids)
        multi_processed_optimize_mock.assert_awaited_once_with(optimizer_settings)

