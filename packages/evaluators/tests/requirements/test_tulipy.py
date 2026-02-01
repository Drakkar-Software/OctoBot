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


import numpy
import tulipy


DATA = numpy.array([81.59, 81.06, 82.87, 83, 83.61,
                    83.15, 82.84, 83.99, 84.55, 84.36,
                    85.53, 86.54, 86.89, 87.77, 87.29])

"""
The goal of these tests is to ensure the Tulipy technical evaluators lib is properly working within pure python 
and cythonized environments.
"""


def test_TA_basics():
    rsi_result = tulipy.rsi(DATA, period=9)
    assert all(74 < v < 86
               for v in rsi_result)
    assert len(rsi_result) == 6
    sma_result = tulipy.sma(DATA, period=9)
    assert all(74 < v < 86
               for v in sma_result)
    assert len(sma_result) == 7
    bands = tulipy.bbands(DATA, period=9, stddev=2)
    assert all(80 < v < 89
               for band in bands
               for v in band)
    assert len(bands) == 3
