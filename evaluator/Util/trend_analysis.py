import talib
import numpy


class TrendAnalysis:

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

        # best case: up the upper band
        if current_interest > current_up:
            return -1

        # worse case: down the lower band
        elif current_interest < current_low:
            return 1

        # average case: approximately on middle band
        elif current_middle + delta > current_interest and current_middle - delta < current_interest:
            micro_change = delta_function(current_interest / current_middle) - 1
            return -1 * micro_change

        # good case: up the middle band
        elif current_middle + delta < current_interest:
            return -1 * (current_interest / delta_up)

        # bad case: down the lower band
        elif current_middle + delta < current_interest:
            return current_interest / delta_low
