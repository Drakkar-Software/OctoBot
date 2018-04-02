import talib

from evaluator.TA.TA_evaluator import TrendEvaluator, PriceStrings


# https://mrjbq7.github.io/ta-lib/func_groups/overlap_studies.html

class CandleAnalysisTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        pass


# directional_movement_index --> trend strength
class DMITrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        pass


# bollinger_bands
class BBTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        upperband, middleband, lowerband = talib.BBANDS(self.data[PriceStrings.STR_PRICE_CLOSE.value])


# ease_of_movement --> ease to change trend --> trend strength
class EOMTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        pass
