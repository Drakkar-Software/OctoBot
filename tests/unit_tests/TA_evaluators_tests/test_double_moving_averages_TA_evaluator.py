import pytest

from tests.unit_tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA import DoubleMovingAverageTrendEvaluator


@pytest.fixture()
def evaluator_tester():
    evaluator_tester_instance = TestDoubleMovingAveragesTAEvaluator()
    evaluator_tester_instance.init(DoubleMovingAverageTrendEvaluator)
    return evaluator_tester_instance


class TestDoubleMovingAveragesTAEvaluator(AbstractTATest):

    @staticmethod
    def test_stress_test(evaluator_tester):
        evaluator_tester.run_stress_test_without_exceptions(0.8)

    @staticmethod
    def test_reactions_to_dump(evaluator_tester):
        evaluator_tester.run_test_reactions_to_dump(0.15, 0.15, -0.35, -0.75, -1)

    @staticmethod
    def test_reactions_to_pump(evaluator_tester):
        evaluator_tester.run_test_reactions_to_pump(0.1, 0.4, 1, 1, 1, 0.96, -0.45)

    @staticmethod
    def test_reaction_to_rise_after_over_sold(evaluator_tester):
        evaluator_tester.run_test_reactions_to_rise_after_over_sold(-0.7, -0.99, -0.99, -0.5, 0.85)

    @staticmethod
    def test_reaction_to_over_bought_then_dip(evaluator_tester):
        evaluator_tester.run_test_reactions_to_over_bought_then_dip(0, 0.4, 0.7, 0.6, -0.9, -0.1)

    @staticmethod
    def test_reaction_to_flat_trend(evaluator_tester):
        evaluator_tester.run_test_reactions_to_flat_trend(
            # eval_start_move_ending_up_in_a_rise,
            0.5,
            # eval_reaches_flat_trend, eval_first_micro_up_p1, eval_first_micro_up_p2,
            1, 0.65, 0.2,
            # eval_micro_down1, eval_micro_up1, eval_micro_down2, eval_micro_up2,
            -0.25, 0, -0.1, 0,
            # eval_micro_down3, eval_back_normal3, eval_micro_down4, eval_back_normal4,
            -0.1, 0, -0.1, 0,
            # eval_micro_down5, eval_back_up5, eval_micro_up6, eval_back_down6,
            0.2, -0.10, 0, 0.1,
            # eval_back_normal6, eval_micro_down7, eval_back_up7, eval_micro_down8,
            -0.05, -0.1, -0.1, -0.15,
            # eval_back_up8, eval_micro_down9, eval_back_up9
            0, -0.1, 0.1)
