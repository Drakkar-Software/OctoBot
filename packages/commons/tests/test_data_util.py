#  Drakkar-Software OctoBot-Commons
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
import numpy as np

from octobot_commons.data_util import drop_nan, mean, shift_value_array


def test_drop_nan():
    assert np.array_equal(drop_nan(np.array([1, np.nan, 2, 3, np.nan])), np.array([1, 2, 3]))
    assert np.array_equal(drop_nan(np.array([np.nan, np.nan, np.nan])), np.array([]))


def test_mean():
    assert mean([1, 2, 3, 4, 5, 6, 7]) == 4.0
    assert mean([0.684, 1, 2, 3, 4, 5.5, 6, 7.5]) == 3.7105
    assert mean([]) == 0


def test_shift_value_array():
    array = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=np.float64)
    np.testing.assert_array_equal(shift_value_array(array, shift_count=-1, fill_value=np.nan),
                                  np.array([2, 3, 4, 5, 6, 7, 8, 9, np.nan], dtype=np.float64))

    array = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9], dtype=np.float64)
    np.testing.assert_array_equal(shift_value_array(array, shift_count=2, fill_value=np.nan),
                                  np.array([np.nan, np.nan, 1, 2, 3, 4, 5, 6, 7], dtype=np.float64))
