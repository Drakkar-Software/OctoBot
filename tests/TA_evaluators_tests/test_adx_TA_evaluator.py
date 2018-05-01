from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import ADXMomentumEvaluator


class TestADXTAEvaluator(AbstractTATest):

    def test_stress_test(self):
        self.init(ADXMomentumEvaluator)
        self.run_stress_test_without_exceptions()
