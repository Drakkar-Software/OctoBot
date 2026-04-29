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
from octobot_commons.number_util import round_into_str_with_max_digits, round_into_float_with_max_digits


def test_round_into_max_digits():
    assert round_into_str_with_max_digits(125.0256, 2) == '125.03'
    assert round_into_float_with_max_digits(125.0210, 2) == 125.02
    assert round_into_float_with_max_digits(1301, 5) == 1301.00000
    assert round_into_float_with_max_digits(59866, 0) == 59866
    assert round_into_float_with_max_digits(1.567824117582484154178, 15) == 1.567824117582484
    assert round_into_float_with_max_digits(0.000000059, 8) == 0.00000006
    assert not round_into_float_with_max_digits(8712661000.1273185137283, 10) == 8712661000.127318
    assert round_into_float_with_max_digits(8712661000.1273185137283, 10) == 8712661000.1273185
    assert round_into_float_with_max_digits(8712661000.1273185137283, 10) == 8712661000.12731851
    assert round_into_float_with_max_digits(8712661000.1273185137283, 10) == 8712661000.127318513
    assert round_into_float_with_max_digits(8712661000.1273185137283, 10) == 8712661000.1273185137
    assert round_into_float_with_max_digits(0.0000000000001, 5) == 0
    assert not round_into_float_with_max_digits(0.0000000000001, 13) == 0

