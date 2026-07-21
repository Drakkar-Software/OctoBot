#  Drakkar-Software OctoBot-Tentacles
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
import copy

import octobot_commons.enums as commons_enums
import tentacles.Evaluator.Strategies as Strategies
import tests.test_utils.config as test_utils_config


def _create_tas_evaluator(
    specific_config: dict,
) -> Strategies.TechnicalAnalysisStrategyEvaluator:
    evaluator = Strategies.TechnicalAnalysisStrategyEvaluator(
        test_utils_config.load_test_tentacles_config()
    )
    evaluator.specific_config = specific_config
    return evaluator


class TestTechnicalAnalysisStrategyEvaluatorInitUserInputs:
    def test_seeds_default_time_frame_weight_when_config_empty(self):
        evaluator = _create_tas_evaluator({})
        evaluator.init_user_inputs({})

        time_frames = evaluator.specific_config[evaluator.TIME_FRAMES_TO_WEIGHT]
        assert len(time_frames) == 1
        assert time_frames[0][evaluator.TIME_FRAME] == commons_enums.TimeFrames.THIRTY_MINUTES.value
        assert time_frames[0][evaluator.WEIGHT] == 30
        assert evaluator.weight_by_time_frames == {
            commons_enums.TimeFrames.THIRTY_MINUTES.value: 30
        }

    def test_preserves_existing_user_time_frame_weights(self):
        user_time_frames = [
            {
                Strategies.TechnicalAnalysisStrategyEvaluator.TIME_FRAME: commons_enums.TimeFrames.ONE_HOUR.value,
                Strategies.TechnicalAnalysisStrategyEvaluator.WEIGHT: 70,
            },
            {
                Strategies.TechnicalAnalysisStrategyEvaluator.TIME_FRAME: commons_enums.TimeFrames.FOUR_HOURS.value,
                Strategies.TechnicalAnalysisStrategyEvaluator.WEIGHT: 20,
            },
        ]
        evaluator = _create_tas_evaluator(
            {
                Strategies.TechnicalAnalysisStrategyEvaluator.TIME_FRAMES_TO_WEIGHT: copy.deepcopy(
                    user_time_frames
                )
            }
        )
        evaluator.init_user_inputs({})

        time_frames = evaluator.specific_config[evaluator.TIME_FRAMES_TO_WEIGHT]
        assert len(time_frames) == 2
        assert time_frames[0][evaluator.TIME_FRAME] == commons_enums.TimeFrames.ONE_HOUR.value
        assert time_frames[0][evaluator.WEIGHT] == 70
        assert time_frames[1][evaluator.TIME_FRAME] == commons_enums.TimeFrames.FOUR_HOURS.value
        assert time_frames[1][evaluator.WEIGHT] == 20
        assert evaluator.weight_by_time_frames == {
            commons_enums.TimeFrames.ONE_HOUR.value: 70,
            commons_enums.TimeFrames.FOUR_HOURS.value: 20,
        }
