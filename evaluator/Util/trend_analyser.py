import talib
import numpy
import math


class TrendAnalyser:

    # Return parabolic proximity to the lower or the upper band relatively to the middle band.
    # If delta function given (threshold fct): linearly compute proximity between middle and delta before parabolic:
    @staticmethod
    def bollinger_trend_analysis(data_frame, delta_function=None):
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
            return 0

        # exactly on the middle
        elif current_value == current_middle:
            return 0

        # up the upper band
        elif current_value > current_up:
            return 1

        # down the lower band
        elif current_value < current_low:
            return -1

        # delta given: use parabolic factor after delta, linear before
        if delta_function:
            delta = delta_function(numpy.mean([delta_up, delta_low]))

            micro_change = ((current_value / current_middle) - 1) / 2

            # approximately on middle band
            if current_middle + delta >= current_value >= current_middle - delta:
                return micro_change

            # up the middle area
            elif current_middle + delta < current_value:
                return max(micro_change, math.pow((current_value - current_middle) / delta_up, 2))

            # down the middle area
            elif current_middle - delta > current_value:
                return -1 * max(micro_change, math.pow((current_middle - current_value) / delta_low, 2))

        # regular values case: use parabolic factor all the time
        else:

            # up the middle band
            if current_middle < current_value:
                return math.pow((current_value - current_middle) / delta_up, 2)

            # down the middle band
            elif current_middle > current_value:
                return -1 * math.pow((current_middle - current_value) / delta_low, 2)


        # should not happen
        return 0

    # trend < 0 --> Down trend
    # trend > 0 --> Up trend
    @staticmethod
    def get_trend(data_frame, averages_to_use):
        trend = 0
        inc = round(1 / len(averages_to_use), 2)
        averages = []

        # Get averages
        for average_to_use in averages_to_use:
            averages.append(data_frame.tail(average_to_use).values.mean())

        for a in range(0, len(averages) - 1):
            if averages[a] - averages[a + 1] > 0:
                trend -= inc
            else:
                trend += inc

        return trend
