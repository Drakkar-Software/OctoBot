import talib
import numpy
from config.cst import START_PENDING_EVAL_NOTE

from evaluator.Util.abstract_util import AbstractUtil


class StatisticAnalysis(AbstractUtil):

    # Return linear proximity to the lower or the upper band relatively to the middle band.
    # Linearly compute proximity between middle and delta before linear:
    @staticmethod
    def analyse_recent_trend_changes(data_frame, delta_function):
        # compute bollinger bands
        upper_band, middle_band, lower_band = talib.BBANDS(data_frame, 20, 2, 2)
        # if close to lower band => low value => bad,
        # therefore if close to middle, value is keeping up => good
        # finally if up the middle one or even close to the upper band => very good

        current_value = data_frame.iloc[-1]
        current_up = upper_band.tail(1).values[0]
        current_middle = middle_band.tail(1).values[0]
        current_low = lower_band.tail(1).values[0]
        delta_up = current_up - current_middle
        delta_low = current_middle - current_low

        # its exactly on all bands
        if current_up == current_low:
            return START_PENDING_EVAL_NOTE

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
