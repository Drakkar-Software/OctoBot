import talib
import numpy

from config.cst import *
from evaluator.Util.trend_analyser import TrendAnalyser
from evaluator.TA.TA_evaluator import TrendEvaluator


# https://mrjbq7.github.io/ta-lib/func_groups/overlap_studies.html
class CandleAnalysisTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        pass


# directional_movement_index --> trend strength
class DMITrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        pass


# bollinger_bands
class BBTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        self.eval_note = TrendAnalyser.bollinger_trend_analysis(self.data[PriceStrings.STR_PRICE_CLOSE.value]
                                                                , numpy.sqrt)


# ease_of_movement --> ease to change trend --> trend strength
class EOMTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        pass
