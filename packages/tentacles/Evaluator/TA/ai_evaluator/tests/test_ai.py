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
import types
import mock
import pytest
import numpy

import tentacles.Evaluator.TA.ai_evaluator as ai_evaluator


@pytest.fixture
def GPT_evaluator():
    return ai_evaluator.GPTEvaluator(mock.Mock(is_tentacle_activated=mock.Mock(return_value=True)))


def test_indicators(GPT_evaluator):
    data = numpy.array([100, 223, 123, 23, 134, 124, 434, 3243, 121, 3242.34, 1212, 87, 232.32])
    for indicator in GPT_evaluator.INDICATORS:
        GPT_evaluator.indicator = indicator
        GPT_evaluator.period = 2
        assert len(data) - (GPT_evaluator.period + 1) <= len(GPT_evaluator.call_indicator(data)) <= len(data)


def test_get_candles_data_api(GPT_evaluator):
    for source in GPT_evaluator.SOURCES:
        GPT_evaluator.source = source
        if GPT_evaluator.source not in GPT_evaluator.get_unformated_sources():
            assert isinstance(GPT_evaluator.get_candles_data_api(), types.FunctionType)


def test_parse_prediction_side(GPT_evaluator):
    assert GPT_evaluator._parse_prediction_side("up 70%") == -1
    assert GPT_evaluator._parse_prediction_side("plop up 70%") == -1
    assert GPT_evaluator._parse_prediction_side(" up with 70%") == -1
    assert GPT_evaluator._parse_prediction_side("Prediction: up with 70% confidence") == -1

    assert GPT_evaluator._parse_prediction_side("down 70%") == 1
    assert GPT_evaluator._parse_prediction_side("plop down 70%") == 1
    assert GPT_evaluator._parse_prediction_side(" down with 70%") == 1
    assert GPT_evaluator._parse_prediction_side("Prediction: down with 70% confidence") == 1


def test_parse_confidence(GPT_evaluator):
    assert GPT_evaluator._parse_confidence("up 70%") == 70
    assert GPT_evaluator._parse_confidence("up 54.33%") == 54.33
    assert GPT_evaluator._parse_confidence("down 70% confidence blablabla") == 70
    assert GPT_evaluator._parse_confidence("Prediction: down 70%") == 70
    GPT_evaluator.min_confidence_threshold = 60
    assert GPT_evaluator._parse_confidence("up 70%") == 100
    assert GPT_evaluator._parse_confidence("up 60%") == 100
    assert GPT_evaluator._parse_confidence("up 59%") == 59
