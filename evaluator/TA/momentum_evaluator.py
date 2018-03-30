from evaluator.TA_evaluator import MomentumEvaluator


class ChaikinOscillatorMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# money_flow_index --> buy and sell pressure
class MFIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


class RSIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


class OBVMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# Negative Volume Index (NVI) --> "Detect smart money"
class NVIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# Positive Volume Index (PVI) --> market noise on particular market conditions
class PVIMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# William's % R --> overbought / oversold
class WilliamsRMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# TRIX --> percent rate-of-change trend
class TRIXMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()


# ultimate_oscillator --> see divergences
class UOMomentumEvaluator(MomentumEvaluator):
    def __init__(self):
        super().__init__()
