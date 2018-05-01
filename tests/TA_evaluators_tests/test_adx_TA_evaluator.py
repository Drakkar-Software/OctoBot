from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import ADXMomentumEvaluator


class TestADXTAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(ADXMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions()

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.2, 0.3, -0.1, -0.1, 0)
