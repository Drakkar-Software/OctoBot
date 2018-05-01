from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.trend_evaluator import DoubleMovingAverageTrendEvaluator


class TestDoubleMovingAveragesTAEvaluator(AbstractTATest):

    def test_stress_test(self):
        self.init(DoubleMovingAverageTrendEvaluator)
        self.run_stress_test_without_exceptions(0.6)
