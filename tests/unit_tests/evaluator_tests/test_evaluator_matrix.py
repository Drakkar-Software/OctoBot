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

import math

from evaluator.evaluator_matrix import EvaluatorMatrix
from tests.test_utils.config import load_test_config
from config import EvaluatorMatrixTypes, TimeFrames


def _get_tools():
    config = load_test_config()
    matrix_inst = EvaluatorMatrix(config)
    matrix = matrix_inst.matrix
    return matrix_inst, matrix, config


def test_init():
    matrix_inst, matrix, config = _get_tools()
    assert EvaluatorMatrixTypes.TA in matrix
    assert EvaluatorMatrixTypes.SOCIAL in matrix
    assert EvaluatorMatrixTypes.REAL_TIME in matrix
    assert EvaluatorMatrixTypes.STRATEGIES in matrix


def test_set_get_eval():
    time_frames = [None, TimeFrames.ONE_HOUR]
    values = [1, 1.02, math.pi, math.nan]
    for time_frame in time_frames:
        matrix_inst, matrix, config = _get_tools()
        for value in values:
            for matrix_type in EvaluatorMatrixTypes:
                key = f"{matrix_type}{value}"
                matrix_inst.set_eval(matrix_type, key, value, time_frame)
                if math.isnan(value):
                    assert matrix_inst.get_eval_note(matrix, matrix_type, key, time_frame) is None
                else:
                    assert matrix_inst.get_eval_note(matrix, matrix_type, key, time_frame) == value
