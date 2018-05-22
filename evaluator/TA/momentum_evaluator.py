"""
CryptoBot Package

$package_description: {
    "name": "momentum_evaluator",
    "type": "TA",
    "version": "1.0.0",
    "requirements": []
}
"""

import math

import talib
from talib._ta_lib import CDLINVERTEDHAMMER, CDLDOJI, CDLSHOOTINGSTAR, CDLHAMMER, CDLHARAMI, CDLPIERCING

from config.cst import *
from evaluator.TA.TA_evaluator import MomentumEvaluator
from tools.data_frame_util import DataFrameUtil
from evaluator.Util.pattern_analysis import PatternAnalyser
from evaluator.Util.trend_analysis import TrendAnalysis


class RSIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.pertinence = 1

    # TODO : temp analysis
    def eval_impl(self):
        if len(self.data):
            rsi_v = talib.RSI(self.data[PriceStrings.STR_PRICE_CLOSE.value])

            if len(rsi_v) and not math.isnan(rsi_v.tail(1)):
                long_trend = TrendAnalysis.get_trend(rsi_v, self.long_term_averages)
                short_trend = TrendAnalysis.get_trend(rsi_v, self.short_term_averages)

                # check if trend change
                if short_trend > 0 > long_trend:
                    # trend changed to up
                    self.set_eval_note(-short_trend)

                elif long_trend > 0 > short_trend:
                    # trend changed to down
                    self.set_eval_note(short_trend)

                # use RSI current value
                last_rsi_value = rsi_v.tail(1).values[0]
                if last_rsi_value > 50:
                    self.set_eval_note(rsi_v.tail(1).values[0] / 200)
                else:
                    self.set_eval_note((rsi_v.tail(1).values[0] - 100) / 200)


# bollinger_bands
class BBMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        self.eval_note = START_PENDING_EVAL_NOTE
        if len(self.data):
            # compute bollinger bands
            upper_band, middle_band, lower_band = talib.BBANDS(self.data[PriceStrings.STR_PRICE_CLOSE.value], 20, 2, 2)
            # if close to lower band => low value => bad,
            # therefore if close to middle, value is keeping up => good
            # finally if up the middle one or even close to the upper band => very good

            # indicators_map = [
            #     {
            #         "title": "upper_band",
            #         "data": upper_band,
            #         "in_graph": True
            #     },
            #     {
            #         "title": "middle_band",
            #         "data": middle_band,
            #         "in_graph": True
            #     },
            #     {
            #         "title": "lower_band",
            #         "data": lower_band,
            #         "in_graph": True
            #     }
            # ]
            # DataVisualiser.show_candlesticks_dataframe_with_indicators(self.data, indicators_map)

            current_value = self.data[PriceStrings.STR_PRICE_CLOSE.value].iloc[-1]
            current_up = upper_band.tail(1).values[0]
            current_middle = middle_band.tail(1).values[0]
            current_low = lower_band.tail(1).values[0]
            delta_up = current_up - current_middle
            delta_low = current_middle - current_low

            # its exactly on all bands
            if current_up == current_low:
                self.eval_note = START_PENDING_EVAL_NOTE

            # exactly on the middle
            elif current_value == current_middle:
                self.eval_note = 0

            # up the upper band
            elif current_value > current_up:
                self.eval_note = 1

            # down the lower band
            elif current_value < current_low:
                self.eval_note = -1

            # regular values case: use parabolic factor all the time
            else:

                # up the middle band
                if current_middle < current_value:
                    self.eval_note = math.pow((current_value - current_middle) / delta_up, 2)

                # down the middle band
                elif current_middle > current_value:
                    self.eval_note = -1 * math.pow((current_middle - current_value) / delta_low, 2)


class CandlePatternMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.pertinence = 1
        self.factor = 0.5

    def update_note(self, pattern_bool):
        last_value = pattern_bool.tail(1).values[0]

        # bullish
        if last_value >= 100:

            # confirmation
            if last_value > 200:
                self.set_eval_note(-2 * self.factor)
            else:
                self.set_eval_note(-1 * self.factor)

        # bearish
        elif last_value <= -100:

            # confirmation
            if last_value > 200:
                self.set_eval_note(2 * self.factor)
            else:
                self.set_eval_note(1 * self.factor)

    def eval_impl(self):
        if len(self.data):
            open_values = self.data[PriceStrings.STR_PRICE_OPEN.value]
            high_values = self.data[PriceStrings.STR_PRICE_HIGH.value]
            low_values = self.data[PriceStrings.STR_PRICE_LOW.value]
            close_values = self.data[PriceStrings.STR_PRICE_CLOSE.value]

            # Inverted Hammer
            # When the low and the open are the same, a bullish Inverted Hammer candlestick is formed and
            # it is considered a stronger bullish sign than when the low and close are the same, forming a bearish
            # Hanging Man (the bearish Hanging Man is still considered bullish, just not as much because the day ended by
            # closing with losses).
            self.update_note(CDLINVERTEDHAMMER(open_values, high_values, low_values, close_values))

            # Hammer
            # The long lower shadow of the Hammer implies that the market tested to find where support and
            # demand was located. When the market found the area of support, the lows of the day, bulls began to push
            # prices higher, near the opening price. Thus, the bearish advance downward was rejected by the bulls.
            self.update_note(CDLHAMMER(open_values, high_values, low_values, close_values))

            # Doji
            # It is important to emphasize that the Doji pattern does not mean reversal, it means indecision.Doji's
            # are often found during periods of resting after a significant move higher or lower; the market,
            # after resting, then continues on its way. Nevertheless, a Doji pattern could be interpreted as a sign that
            # a prior trend is losing its strength, and taking some profits might be well advised.
            self.update_note(CDLDOJI(open_values, high_values, low_values, close_values))

            # Shooting star
            # The Shooting Star formation is considered less bearish, but nevertheless bearish when the
            # open and low are roughly the same. The bears were able to counteract the bulls, but were not able to bring
            # the price back to the price at the open.
            # The long upper shadow of the Shooting Star implies that the market tested to find where resistance and
            # supply was located. When the market found the area of resistance, the highs of the day, bears began to push
            #  prices lower, ending the day near the opening price. Thus, the bullish advance upward was rejected by the
            # bears.
            self.update_note(CDLSHOOTINGSTAR(open_values, high_values, low_values, close_values))

            # Harami A buy signal could be triggered when the day after the bullish Harami occured, price rose higher,
            # closing above the downward resistance trendline. A bullish Harami pattern and a trendline break is a
            # combination that potentially could resulst in a buy signal. A sell signal could be triggered when the day
            # after the bearish Harami occured, price fell even further down, closing below the upward support trendline.
            #  When combined, a bearish Harami pattern and a trendline break might be interpreted as a potential sell
            # signal.
            self.update_note(CDLHARAMI(open_values, high_values, low_values, close_values))

            # Piercing Line
            # Pattern Bullish Engulfing Pattern (see: Bullish Engulfing Pattern) is typically viewed as
            # being more bullish than the Piercing Pattern because it completely reverses the losses of Day 1 and adds
            # new gains.
            self.update_note(CDLPIERCING(open_values, high_values, low_values, close_values))

            # if neutral
            if self.eval_note == 0 or self.eval_note is None:
                self.eval_note = START_PENDING_EVAL_NOTE
        elif not self.eval_note:
            self.eval_note = START_PENDING_EVAL_NOTE


# ADX --> trend_strength
class ADXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    # implementation according to: https://www.investopedia.com/articles/technical/02/041002.asp => length = 14 and
    # exponential moving average = 20 in a uptrend market
    # idea: adx > 30 => strong trend, < 20 => trend change to come
    def eval_impl(self):
        self.eval_note = START_PENDING_EVAL_NOTE
        if len(self.data):
            min_adx = 7.5
            max_adx = 45
            neutral_adx = 25
            adx = talib.ADX(self.data[PriceStrings.STR_PRICE_HIGH.value],
                            self.data[PriceStrings.STR_PRICE_LOW.value],
                            self.data[PriceStrings.STR_PRICE_CLOSE.value],
                            timeperiod=14)
            instant_ema = talib.EMA(self.data[PriceStrings.STR_PRICE_CLOSE.value], timeperiod=2)
            slow_ema = talib.EMA(self.data[PriceStrings.STR_PRICE_CLOSE.value], timeperiod=20)
            adx = DataFrameUtil.drop_nan_and_reset_index(adx)

            if len(adx):
                current_adx = adx.iloc[-1]
                current_slows_ema = slow_ema.iloc[-1]
                current_instant_ema = instant_ema.iloc[-1]

                multiplier = -1 if current_instant_ema < current_slows_ema else 1

                # strong adx => strong trend
                if current_adx > neutral_adx:
                    # if max adx already reached => when ADX forms a top and begins to turn down, you should look for a
                    # retracement that causes the price to move toward its 20-day exponential moving average (EMA).
                    adx_last_values = adx.tail(15)
                    adx_last_value = adx_last_values.iloc[-1]

                    local_max_adx = adx_last_values.max()
                    # max already reached => trend will slow down
                    if adx_last_value < local_max_adx:

                        self.eval_note = multiplier * (current_adx - neutral_adx) / (local_max_adx - neutral_adx)

                    # max not reached => trend will continue, return chances to be max now
                    else:
                        crossing_indexes = TrendAnalysis.get_threshold_change_indexes(adx, neutral_adx)
                        chances_to_be_max = \
                            TrendAnalysis.get_estimation_of_move_state_relatively_to_previous_moves_length(
                                crossing_indexes, adx) if len(crossing_indexes) > 2 \
                                else 0.75
                        proximity_to_max = min(1, current_adx / max_adx)
                        self.eval_note = multiplier * proximity_to_max * chances_to_be_max

                # weak adx => change to come
                else:
                    self.eval_note = multiplier * min(1, ((neutral_adx - current_adx) / (neutral_adx - min_adx)))


class OBVMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        obv_v = talib.OBV(self.data[PriceStrings.STR_PRICE_CLOSE.value],
                          self.data[PriceStrings.STR_PRICE_VOL.value])


# William's % R --> overbought / oversold
class WilliamsRMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        willr_v = talib.WILLR(self.data[PriceStrings.STR_PRICE_HIGH.value],
                              self.data[PriceStrings.STR_PRICE_LOW.value],
                              self.data[PriceStrings.STR_PRICE_CLOSE.value])


# TRIX --> percent rate-of-change trend
class TRIXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        trix_v = talib.TRIX(self.data[PriceStrings.STR_PRICE_CLOSE.value])


class MACDMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.previous_note = None

    def eval_impl(self):
        self.eval_note = START_PENDING_EVAL_NOTE
        if len(self.data):
            macd, macd_signal, macd_hist = talib.MACD(self.data[PriceStrings.STR_PRICE_CLOSE.value],
                                                      fastperiod=12,
                                                      slowperiod=26,
                                                      signalperiod=9)

            # on macd hist => M pattern: bearish movement, W pattern: bullish movement
            #                 max on hist: optimal sell or buy
            macd_hist = DataFrameUtil.drop_nan_and_reset_index(macd_hist)
            zero_crossing_indexes = TrendAnalysis.get_threshold_change_indexes(macd_hist, 0)
            last_index = len(macd_hist.index) - 1
            pattern, start_index, end_index = PatternAnalyser.find_pattern(macd_hist, zero_crossing_indexes, last_index)

            if pattern != PatternAnalyser.UNKNOWN_PATTERN:

                # set sign (-1 buy or 1 sell)
                signe_multiplier = -1 if pattern == "W" or pattern == "V" else 1

                # set pattern time frame => W and M are on 2 time frames, others 1
                pattern_move_time = 2 if (pattern == "W" or pattern == "M") and end_index == last_index else 1

                # set weight according to the max value of the pattern and the current value
                current_pattern_start = start_index
                price_weight = macd_hist.iloc[-1] / macd_hist[current_pattern_start:].max() if signe_multiplier == 1 \
                    else macd_hist.iloc[-1] / macd_hist[current_pattern_start:].min()

                if not math.isnan(price_weight):

                    # add pattern's strength
                    weight = price_weight * PatternAnalyser.get_pattern_strength(pattern)

                    average_pattern_period = 0.7
                    if len(zero_crossing_indexes) > 1:
                        # compute chances to be after average pattern period
                        patterns = [PatternAnalyser.get_pattern(
                            macd_hist[zero_crossing_indexes[i]:zero_crossing_indexes[i + 1]])
                            for i in range(len(zero_crossing_indexes) - 1)
                        ]
                        if 0 != zero_crossing_indexes[0]:
                            patterns.append(PatternAnalyser.get_pattern(macd_hist[0:zero_crossing_indexes[0]]))
                        if len(macd_hist) - 1 != zero_crossing_indexes[-1]:
                            patterns.append(PatternAnalyser.get_pattern(macd_hist[zero_crossing_indexes[-1]:]))
                        double_patterns_count = patterns.count("W") + patterns.count("M")

                        average_pattern_period = TrendAnalysis. \
                            get_estimation_of_move_state_relatively_to_previous_moves_length(
                            zero_crossing_indexes,
                            macd_hist,
                            pattern_move_time,
                            double_patterns_count)

                    # if we have few data but wave is growing => set higher value
                    if len(zero_crossing_indexes) <= 1 and price_weight == 1:
                        if self.previous_note is not None:
                            average_pattern_period = 0.95
                        self.previous_note = signe_multiplier * weight * average_pattern_period
                    else:
                        self.previous_note = None

                    self.eval_note = signe_multiplier * weight * average_pattern_period


class ChaikinOscillatorMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        pass


class StochasticMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval_impl(self):
        slowk, slowd = talib.STOCH(self.data[PriceStrings.STR_PRICE_HIGH.value],
                                   self.data[PriceStrings.STR_PRICE_LOW.value],
                                   self.data[PriceStrings.STR_PRICE_CLOSE.value])
