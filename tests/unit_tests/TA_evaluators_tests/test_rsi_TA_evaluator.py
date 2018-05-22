from tests.unit_tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA import RSIMomentumEvaluator


class TestRSITAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(RSIMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions(0.7, False)

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(0.3, -0.2, -0.8, -1, -1)

    def test_reactions_to_pump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_pump(0.3, 0.6, 1, 1, 1, 1, 0.5)

    def test_reaction_to_rise_after_over_sold(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_rise_after_over_sold(-1, -1, -1, -1, -1)

    def test_reaction_to_over_bought_then_dip(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_over_bought_then_dip(0.1, 0.4, 0.85, 1, 0.75, 0.8)

    def test_reaction_to_flat_trend(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_flat_trend(
            # eval_start_move_ending_up_in_a_rise,
            0.4,
            # eval_reaches_flat_trend, eval_first_micro_up_p1, eval_first_micro_up_p2,
            0.55, 1, 1,
            # eval_micro_down1, eval_micro_up1, eval_micro_down2, eval_micro_up2,
            -0.6, 1, 1, 0.7,
            # eval_micro_down3, eval_back_normal3, eval_micro_down4, eval_back_normal4,
            -0.8, -0.7, 0.75, 0.77,
            # eval_micro_down5, eval_back_up5, eval_micro_up6, eval_back_down6,
            0.2, -0.45, -0.45, -0.1,
            # eval_back_normal6, eval_micro_down7, eval_back_up7, eval_micro_down8,
            0.1, 0.75, 0.4, -1,
            # eval_back_up8, eval_micro_down9, eval_back_up9
            -1, -1, -0.75)
