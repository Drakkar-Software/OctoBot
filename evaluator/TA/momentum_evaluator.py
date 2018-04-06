import talib

from config.cst import *
from evaluator.TA.TA_evaluator import MomentumEvaluator


# https://mrjbq7.github.io/ta-lib/func_groups/momentum_indicators.html

class RSIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.pertinence = 1

    # TODO : temp analysis
    def eval_impl(self):
        rsi_v = talib.RSI(self.data[PriceStrings.STR_PRICE_CLOSE.value])

        long_trend = self.get_trend(rsi_v, self.long_term_averages)
        short_trend = self.get_trend(rsi_v, self.short_term_averages)

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
            self.set_eval_note(rsi_v.tail(1).values[0] / 100)
        else:
            self.set_eval_note((rsi_v.tail(1).values[0] - 100) / 100)


# ADX --> trend_strength
class ADXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    # TODO : temp analysis
    def eval_impl(self):
        adx_v = talib.ADX(self.data[PriceStrings.STR_PRICE_HIGH.value],
                          self.data[PriceStrings.STR_PRICE_LOW.value],
                          self.data[PriceStrings.STR_PRICE_CLOSE.value])

        last = adx_v.tail(1).values

        # An ADX above 30 on the scale indicates there is a strong trend
        if last > 30:
            pass

        # When ADX drops below 18, it often leads to a sideways or horizontal trading pattern
        elif last < 18:
            pass


class OBVMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        obv_v = talib.OBV(self.data[PriceStrings.STR_PRICE_CLOSE.value],
                          self.data[PriceStrings.STR_PRICE_VOL.value])


# William's % R --> overbought / oversold
class WilliamsRMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        willr_v = talib.WILLR(self.data[PriceStrings.STR_PRICE_HIGH.value],
                              self.data[PriceStrings.STR_PRICE_LOW.value],
                              self.data[PriceStrings.STR_PRICE_CLOSE.value])


# TRIX --> percent rate-of-change trend
class TRIXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        trix_v = talib.TRIX(self.data[PriceStrings.STR_PRICE_CLOSE.value])


class MACDMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        macd_v = talib.MACD(self.data[PriceStrings.STR_PRICE_CLOSE.value])


class ChaikinOscillatorMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        pass


class StochasticMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        slowk, slowd = talib.STOCH(self.data[PriceStrings.STR_PRICE_HIGH.value],
                                   self.data[PriceStrings.STR_PRICE_LOW.value],
                                   self.data[PriceStrings.STR_PRICE_CLOSE.value])
