from evaluator.TA_evaluator import TAEvaluator


class TrendEvaluator(TAEvaluator):
    def __init__(self):
        super().__init__()


# directional_movement_index --> trend strength
class DMITrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()


# ease_of_movement --> ease to change trend --> trend strength
class EOMTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()


# ADX --> trend_strength
class ADXMomentumEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
