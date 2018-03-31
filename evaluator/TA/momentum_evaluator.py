from evaluator.TA.TA_evaluator import MomentumEvaluator
from tools.indicator import rsi


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

    # TODO : temp analysis
    def eval(self):
        rsi_v = rsi(self.data)

        # get the last 10 values of RSI
        last_values = rsi_v.tail(10)["rsi"]

        first = last_values.iloc[0]
        last = last_values.iloc[-1]

        # Difference between the last 10 candles
        # if first > last:
        #     self.eval_note -= (first-last)
        # else:
        #     self.eval_note += (last - first)

        if last > 50:
            self.eval_note += last - 0.5
        else:
            self.eval_note -= 0.5 - last


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
