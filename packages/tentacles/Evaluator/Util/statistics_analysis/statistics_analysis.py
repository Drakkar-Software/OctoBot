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
import tulipy
import numpy

import octobot_commons.constants as commons_constants


class StatisticAnalysis:

    # Return linear proximity to the lower or the upper band relatively to the middle band.
    # Linearly compute proximity between middle and delta before linear:
    @staticmethod
    def analyse_recent_trend_changes(data, delta_function):
        # compute bollinger bands
        lower_band, middle_band, upper_band = tulipy.bbands(data, 20, 2)
        # if close to lower band => low value => bad,
        # therefore if close to middle, value is keeping up => good
        # finally if up the middle one or even close to the upper band => very good

        current_value = data[-1]
        current_up = upper_band[-1]
        current_middle = middle_band[-1]
        current_low = lower_band[-1]
        delta_up = current_up - current_middle
        delta_low = current_middle - current_low

        # its exactly on all bands
        if current_up == current_low:
            return commons_constants.START_PENDING_EVAL_NOTE

        # exactly on the middle
        elif current_value == current_middle:
            return 0

        # up the upper band
        elif current_value > current_up:
            return -1

        # down the lower band
        elif current_value < current_low:
            return 1

        # delta given: use parabolic factor after delta, linear before
        delta = delta_function(numpy.mean([delta_up, delta_low]))

        micro_change = ((current_value / current_middle) - 1) / 2

        # approximately on middle band
        if current_middle + delta >= current_value >= current_middle - delta:
            return micro_change

        # up the middle area
        elif current_middle + delta < current_value:
            return -1 * max(micro_change, (current_value - current_middle) / delta_up)

        # down the middle area
        elif current_middle - delta > current_value:
            return max(micro_change, (current_middle - current_value) / delta_low)

        # should not happen
        return 0
