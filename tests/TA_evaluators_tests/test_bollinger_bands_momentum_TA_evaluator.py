from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import BBMomentumEvaluator


class TestBollingerBandsMomentumTAEvaluator(AbstractTATest):

    def test_stress_test(self):
        self.init(BBMomentumEvaluator)
        self.run_stress_test_without_exceptions()

    def test_reactions_to_dump(self):
        self.init(BBMomentumEvaluator)
        self.run_test_reactions_to_dump(0.7, 0.2, -1, -1, -1)
