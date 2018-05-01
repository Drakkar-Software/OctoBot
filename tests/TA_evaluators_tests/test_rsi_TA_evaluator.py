from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import RSIMomentumEvaluator


class TestRSITAEvaluator(AbstractTATest):

    def test_stress_test(self):
        self.init(RSIMomentumEvaluator)
        self.run_stress_test_without_exceptions(0.7, False)
