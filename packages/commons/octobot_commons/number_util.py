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
import decimal
import math
import typing


def round_into_str_with_max_digits(number: float, digits_count: int) -> str:
    """
    Round the number with digits_count
    :param number: the number to round
    :param digits_count: the digit count
    :return: the rounded number
    """
    return "{:.{}f}".format(round(number, digits_count), digits_count)


def round_into_float_with_max_digits(number: float, digits_count: int) -> float:
    """
    Round the float number with digits_count
    :param number: the number to round
    :param digits_count: the digit count
    :return: the rounded number
    """
    return float(
        round_into_str_with_max_digits(number=number, digits_count=digits_count)
    )


def get_digits_count(value: typing.Union[float, decimal.Decimal]):
    """
    :return: the number of digits in the given number
    """
    return round(abs(math.log(value, 10)))
