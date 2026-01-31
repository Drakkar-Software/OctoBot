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

import numpy as np
import math


class PatternAnalyser:

    UNKNOWN_PATTERN = "?"

    # returns the starting and ending index of the pattern if it's found
    # supported patterns:
    # W, M, N and V (ex: for macd)
    # return boolean (pattern found or not), start index and end index
    @staticmethod
    def find_pattern(data, zero_crossing_indexes, data_frame_max_index):
        if len(zero_crossing_indexes) > 1:

            last_move_data = data[zero_crossing_indexes[-1]:]

            # if last_move_data is shaped in W
            shape = PatternAnalyser.get_pattern(last_move_data)

            if shape == "N" or shape == "V":
                # check presence of W or M with insignificant move in the other direction
                backwards_index = 2
                while backwards_index < len(zero_crossing_indexes) and \
                        zero_crossing_indexes[-1*backwards_index] - zero_crossing_indexes[-1*backwards_index-1] < 4:
                    backwards_index += 1
                extended_last_move_data = data[zero_crossing_indexes[-1 * backwards_index]:]
                extended_shape = PatternAnalyser.get_pattern(extended_last_move_data)

                if extended_shape == "W" or extended_shape == "M":
                    # check that values are on the same side (< or >0)
                    first_part = data[zero_crossing_indexes[-1 * backwards_index]:
                                      zero_crossing_indexes[-1*backwards_index+1]]
                    second_part = data[zero_crossing_indexes[-1]:]
                    if np.mean(first_part)*np.mean(second_part) > 0:
                        return extended_shape, zero_crossing_indexes[-1*backwards_index], zero_crossing_indexes[-1]

            return shape, zero_crossing_indexes[-1], data_frame_max_index
        else:
            # if very few data: proceed with basic analysis

            # if last_move_data is shaped in W
            start_pattern_index = 0 if not zero_crossing_indexes else zero_crossing_indexes[0]
            shape = PatternAnalyser.get_pattern(data[start_pattern_index:])
            return shape, start_pattern_index, data_frame_max_index

    @staticmethod
    def get_pattern(data):
        if len(data) > 0:
            mean_value = np.mean(data) * 0.7
        else:
            mean_value = math.nan
        if math.isnan(mean_value):
            return PatternAnalyser.UNKNOWN_PATTERN
        indexes_under_mean_value = np.where(data > mean_value)[0] \
            if mean_value < 0 \
            else np.where(data < mean_value)[0]

        nb_gaps = 0
        for i in range(len(indexes_under_mean_value)-1):
            if indexes_under_mean_value[i+1]-indexes_under_mean_value[i] > 3:
                nb_gaps += 1

        if nb_gaps > 1:
            return "W" if mean_value < 0 else "M"
        else:
            return "V" if mean_value < 0 else "N"

    # returns a value 0 < value < 1: the higher the stronger is the pattern
    @staticmethod
    def get_pattern_strength(pattern):
        if pattern == "W" or pattern == "M":
            return 1
        elif pattern == "N" or pattern == "V":
            return 0.75
        return 0
