from config.cst import EvaluatorClasses
from evaluator.TA_evaluator import TrendEvaluator


# directional_movement_index --> trend strength
class DMITrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# ease_of_movement --> ease to change trend --> trend strength
class EOMTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# ADX --> trend_strength
class ADXTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


class TrendEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            ADXTrendEvaluator(),
            EOMTrendEvaluator(),
            DMITrendEvaluator()
        ]
