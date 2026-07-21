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

import tentacles.Evaluator.TA as TA
import tests.test_utils.config as test_utils_config


def _create_rsi_weight_evaluator(
    specific_config: dict,
) -> TA.RSIWeightMomentumEvaluator:
    evaluator = TA.RSIWeightMomentumEvaluator(test_utils_config.load_test_tentacles_config())
    evaluator.specific_config = specific_config
    return evaluator


class TestRSIWeightMomentumEvaluatorInitUserInputs:
    def test_seeds_default_weight_when_config_empty(self):
        evaluator = _create_rsi_weight_evaluator({})
        evaluator.init_user_inputs({})

        weights = evaluator.specific_config[evaluator.RSI_TO_WEIGHTS]
        assert len(weights) == 1
        assert weights[0][evaluator.SLOW_THRESHOLD] == 30
        assert len(weights[0][evaluator.FAST_THRESHOLDS]) == 1
        assert weights[0][evaluator.FAST_THRESHOLDS][0][evaluator.FAST_THRESHOLD] == 20
        assert weights[0][evaluator.FAST_THRESHOLDS][0][evaluator.WEIGHTS] == {
            evaluator.PRICE: 2,
            evaluator.VOLUME: 2,
        }
        assert evaluator.weights == weights

    def test_preserves_existing_user_weights(self):
        user_weights = [
            {
                "slow_threshold": 35,
                "fast_thresholds": [
                    {
                        "fast_threshold": 25,
                        "weights": {"price": 3, "volume": 1},
                    }
                ],
            },
            {
                "slow_threshold": 40,
                "fast_thresholds": [
                    {
                        "fast_threshold": 15,
                        "weights": {"price": 1, "volume": 2},
                    }
                ],
            },
        ]
        evaluator = _create_rsi_weight_evaluator(
            {TA.RSIWeightMomentumEvaluator.RSI_TO_WEIGHTS: copy.deepcopy(user_weights)}
        )
        evaluator.init_user_inputs({})

        weights = evaluator.specific_config[evaluator.RSI_TO_WEIGHTS]
        assert len(weights) == 2
        assert weights[0][evaluator.SLOW_THRESHOLD] == 35
        assert weights[0][evaluator.FAST_THRESHOLDS][0][evaluator.FAST_THRESHOLD] == 25
        assert weights[0][evaluator.FAST_THRESHOLDS][0][evaluator.WEIGHTS] == {
            evaluator.PRICE: 3,
            evaluator.VOLUME: 1,
        }
        assert weights[1][evaluator.SLOW_THRESHOLD] == 40
        assert [weight[evaluator.SLOW_THRESHOLD] for weight in evaluator.weights] == [35, 40]
