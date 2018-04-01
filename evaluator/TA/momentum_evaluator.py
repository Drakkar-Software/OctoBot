import talib

from evaluator.TA.TA_evaluator import MomentumEvaluator, PriceStrings


class ChaikinOscillatorMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# money_flow_index --> buy and sell pressure
class MFIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


class RSIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
        self.pertinence = 2

    # TODO : temp analysis
    def eval(self):
        rsi_v = talib.RSI(self.data[PriceStrings.STR_PRICE_CLOSE.value])

        # get the last 10 values of RSI
        last_values = rsi_v.tail(10).values

        first = last_values[0]
        last = last_values[-1]

        rsi_eval = self.eval_note

        # Difference between the last 10 candles
        if first > last:
            rsi_eval -= (first - last)
        else:
            rsi_eval += (last - first)

        if last > 50:
            rsi_eval += last - 0.5
        else:
            rsi_eval -= 0.5 - last

        # 2 : modifications
        self.eval_note += rsi_eval / 2


class OBVMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# Negative Volume Index (NVI) --> "Detect smart money"
class NVIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# Positive Volume Index (PVI) --> market noise on particular market conditions
class PVIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# William's % R --> overbought / oversold
class WilliamsRMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# TRIX --> percent rate-of-change trend
class TRIXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# ultimate_oscillator --> see divergences
class UOMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass
