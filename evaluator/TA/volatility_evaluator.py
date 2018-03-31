# average_true_range
from config.cst import EvaluatorClasses
from evaluator.TA_evaluator import VolatilityEvaluator


class ATRVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# bollinger_bands
class BBVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


# mass index
class MassIndexVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


class ChaikinVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


class VolatilityEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            ChaikinVolatilityEvaluator(),
            MassIndexVolatilityEvaluator(),
            BBVolatilityEvaluator(),
            ATRVolatilityEvaluator()
        ]