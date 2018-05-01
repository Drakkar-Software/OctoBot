from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import RSIMomentumEvaluator


class TestRSITAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(RSIMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions(0.7, False)

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.3, -0.2, -0.8, -1, -1)
