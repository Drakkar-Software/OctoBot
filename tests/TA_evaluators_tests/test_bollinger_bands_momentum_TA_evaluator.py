from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import BBMomentumEvaluator


class TestBollingerBandsMomentumTAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(BBMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions()

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.7, 0.2, -1, -1, -1)

    def test_reaction_to_rise_after_over_sold(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_rise_after_over_sold(-0.1, -0.99, -0.99, -0.5, 1)
