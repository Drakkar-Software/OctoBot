from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.trend_evaluator import DoubleMovingAverageTrendEvaluator


class TestDoubleMovingAveragesTAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(DoubleMovingAverageTrendEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions(0.8)

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.15, 0.15, -0.35, -0.75, -1)

    def test_reaction_to_rise_after_over_sold(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_rise_after_over_sold(-0.7, -0.99, -0.99, -0.5, 0.85)

    def test_reaction_to_over_bought_then_dip(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_over_bought_then_dip(0, 0.4, 0.7, 0.6, -0.9, -0.1)
