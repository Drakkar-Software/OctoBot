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


from typing import Dict, Union, NewType

from config import EvaluatorMatrixTypes

MatrixValueType = NewType('MatrixValueType', Union[str, int, float])
MatrixType = NewType('MatrixType', Dict[str, Dict[str, Union[MatrixValueType, Dict[str, MatrixValueType]]]])


def default_matrix_value():
    return {
        EvaluatorMatrixTypes.TA: {},
        EvaluatorMatrixTypes.SOCIAL: {},
        EvaluatorMatrixTypes.REAL_TIME: {},
        EvaluatorMatrixTypes.STRATEGIES: {}
    }
