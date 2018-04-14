import talib
import numpy
import math


class TrendAnalyser:

    @staticmethod
    def bollinger_trend_analysis(data_frame, delta_function):
        # compute bollinger bands
        upper_band, middle_band, lower_band = talib.BBANDS(data_frame)
        # if close to lower band => low interest => bad,
        # therefore if close to middle, interest is keeping up => good
        # finally if up the middle one or even close to the upper band => very good

        current_interest = data_frame.iloc[-1]
        current_up = upper_band[-1]
        current_middle = middle_band[-1]
        current_low = lower_band[-1]

        delta_up = current_up - current_middle
        delta_low = current_middle - current_low
        delta = delta_function(numpy.mean([delta_up, delta_low]))
        exp_one = math.exp(1)

        # best case: up the upper band
        if current_interest > current_up:
            return -1

        # worse case: down the lower band
        elif current_interest < current_low:
            return 1

        # average case: approximately on middle band
        elif current_middle + delta >= current_interest >= current_middle - delta:
            micro_change = ((current_interest / current_middle) - 1) / 2
            return -1 * micro_change

        # good case: up the middle band
        elif current_middle + delta < current_interest:
            return -1 * math.exp((current_interest - current_middle) / delta_up) / exp_one

        # bad case: down the lower band
        elif current_middle - delta > current_interest:
            return math.exp((current_middle - current_interest) / delta_low) / exp_one

        # should not happen
        else:
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
