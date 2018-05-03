from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import ADXMomentumEvaluator


class TestADXTAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(ADXMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions(0.7)

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.2, 0.3, -0.1, -0.1, -0.4)

    def test_reactions_to_pump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_pump(0, 0.1, 0.45, 0.7, 0.6, 0.65, 0.75)

    def test_reaction_to_rise_after_over_sold(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_rise_after_over_sold(0.8, -0.1, -0.5, -0.52, -0.8)

    def test_reaction_to_over_bought_then_dip(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_over_bought_then_dip(0.1, 0.1, 0.3, 0.4, -0.4, 0.2)
