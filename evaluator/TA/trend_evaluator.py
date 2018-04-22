from config.cst import *
import numpy
import talib

from evaluator.TA.TA_evaluator import TrendEvaluator
from evaluator.Util.trend_analyser import TrendAnalyser


# evaluates position of the current (1 unit) average trend relatively to the 5 units average and 10 units average trend
class TripleMovingAverageTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = True

    def eval_impl(self):
        time_units = [5, 10, 20]
        current_moving_average = talib.MA(self.data[PriceStrings.STR_PRICE_CLOSE.value], timeperiod=2, matype=0)
        results = [TrendAnalyser.get_moving_average_analysis(self.data[PriceStrings.STR_PRICE_CLOSE.value],
                                                             current_moving_average,
                                                             i)
                   for i in time_units]
        self.eval_note = numpy.mean(results)


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
        pass


# ease_of_movement --> ease to change trend --> trend strength
class EOMTrendEvaluator(TrendEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval_impl(self):
        pass
