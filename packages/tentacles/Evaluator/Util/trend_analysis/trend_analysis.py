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


class TrendAnalysis:

    # trend < 0 --> Down trend
    # trend > 0 --> Up trend
    @staticmethod
    def get_trend(data, averages_to_use):
        trend = 0
        inc = round(1 / len(averages_to_use), 2)
        averages = []

        # Get averages
        for average_to_use in averages_to_use:
            data_to_mean = data[-average_to_use:]
            if len(data_to_mean):
                averages.append(np.mean(data_to_mean))
            else:
                averages.append(0)

        for a in range(0, len(averages) - 1):
            if averages[a] - averages[a + 1] > 0:
                trend -= inc
            else:
                trend += inc

        return trend

    @staticmethod
    def peak_has_been_reached_already(data, neutral_val=0):
        if len(data) > 1:
            min_val = min(data)
            max_val = max(data)
            current_val = data[-1] / 0.8
            if current_val > neutral_val:
                return current_val < max_val
            else:
                return current_val > min_val
        else:
            return False

    @staticmethod
    def min_has_just_been_reached(data, acceptance_window=0.8, delay=1):
        if len(data) > 1:
            min_val = min(data)
            current_val = data[-1] / acceptance_window
            accepted_delayed_min = data[-(delay+1):]
            return bool(min_val in accepted_delayed_min and current_val > min_val)
        else:
            return False

    @staticmethod
    # TODO
    def detect_divergence(data_frame, indicator_data_frame):
        pass
        # candle_data = data_frame.tail(DIVERGENCE_USED_VALUE)
        # indicator_data = indicator_data_frame.tail(DIVERGENCE_USED_VALUE)
        #
        # total_delta = []
        #
        # for i in range(0, DIVERGENCE_USED_VALUE - 1):
        #     candle_delta = candle_data.values[i] - candle_data.values[i + 1]
        #     indicator_delta = indicator_data.values[i] - indicator_data.values[i + 1]
        #     total_delta.append(candle_delta - indicator_delta)

    @staticmethod
    def get_estimation_of_move_state_relatively_to_previous_moves_length(mean_crossing_indexes,
                                                                         current_trend,
                                                                         pattern_move_size=1,
                                                                         double_size_patterns_count=0):

        if mean_crossing_indexes:
            # compute average move size
            time_averages = [(lambda a: mean_crossing_indexes[a+1]-mean_crossing_indexes[a])(a)
                             for a in range(len(mean_crossing_indexes)-1)]
            # add 1st length
            if 0 != mean_crossing_indexes[0]:
                time_averages.append(mean_crossing_indexes[0])

            # take double_size_patterns_count into account
            time_averages += [0]*double_size_patterns_count

            time_average = np.mean(time_averages)*pattern_move_size if time_averages else 0

            current_move_length = len(current_trend) - mean_crossing_indexes[-1]
            # higher than time_average => high chances to be at half of the move already
            if current_move_length > time_average/2:
                return 1
            else:
                return current_move_length / (time_average/2)
        else:
            return 0

    @staticmethod
    def get_threshold_change_indexes(data, threshold):

        # sub threshold values
        sub_threshold_indexes = np.where(data <= threshold)[0]

        # remove consecutive sub-threshold values because they are not crosses
        threshold_crossing_indexes = []
        current_move_size = 1
        for i, index in enumerate(sub_threshold_indexes):
            if not len(threshold_crossing_indexes):
                threshold_crossing_indexes.append(index)
            else:
                if threshold_crossing_indexes[-1] == index - current_move_size:
                    current_move_size += 1
                else:
                    if sub_threshold_indexes[i-1] not in threshold_crossing_indexes:
                        threshold_crossing_indexes.append(sub_threshold_indexes[i-1])
                    if index not in threshold_crossing_indexes:
                        threshold_crossing_indexes.append(index)
                    current_move_size = 1
        # add last index if data_frame ends above threshold and last threshold_crossing_indexes inferior
        # to data_frame size
        if len(sub_threshold_indexes) > 0 \
                and sub_threshold_indexes[-1] < len(data) \
                and data[-1] > threshold \
                and sub_threshold_indexes[-1]+1 not in threshold_crossing_indexes:
            threshold_crossing_indexes.append(sub_threshold_indexes[-1]+1)

        return threshold_crossing_indexes

    @staticmethod
    def have_just_crossed_over(list_1, list_2):
        # returns True if the last value of list_1 is higher than the last value of list_2 but the immediately
        # preceding list_1 value is lower than the one from list_2
        try:
            return list_1[-1] > list_2[-1] and list_1[-2] < list_2[-2]
        except KeyError:
            return False
