from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import MACDMomentumEvaluator


class TestMACDTAEvaluator(AbstractTATest):

    def test_stress_test(self):
        self.init(MACDMomentumEvaluator)
        self.run_stress_test_without_exceptions(0.4)
