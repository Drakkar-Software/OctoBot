from evaluator.TA.TA_evaluator import TAEvaluator


class VolatilityEvaluator(TAEvaluator):
    def __init__(self):
        super().__init__()


# average_true_range
class ATRVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()


# bollinger_bands
class BBVolatilityEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()


# mass index
class MassIndexTrendEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()


class ChaikinTrendEvaluator(VolatilityEvaluator):
    def __init__(self):
        super().__init__()
