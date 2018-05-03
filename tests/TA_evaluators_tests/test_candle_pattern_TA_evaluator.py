from tests.TA_evaluators_tests.abstract_TA_test import AbstractTATest
from evaluator.TA.momentum_evaluator import CandlePatternMomentumEvaluator
from config.cst import START_PENDING_EVAL_NOTE


class TestCandlePatternTAEvaluator(AbstractTATest):

    def init_test_with_evaluator_to_test(self):
        self.init(CandlePatternMomentumEvaluator)

    def test_stress_test(self):
        self.init_test_with_evaluator_to_test()
        self.run_stress_test_without_exceptions(0.7, False)

    def test_reactions_to_dump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_dump(START_PENDING_EVAL_NOTE, START_PENDING_EVAL_NOTE, START_PENDING_EVAL_NOTE,
                                        START_PENDING_EVAL_NOTE, -0.5)

    def test_reactions_to_pump(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_pump(-0.5, -0.5,
                                        -0.5, -0.5,
                                        -0.5, -0.5,
                                        -0.5)

    def test_reaction_to_rise_after_over_sold(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_rise_after_over_sold(START_PENDING_EVAL_NOTE, START_PENDING_EVAL_NOTE, -0.5,
                                                        -0.5, -0.5)

    def test_reaction_to_over_bought_then_dip(self):
        self.init_test_with_evaluator_to_test()
        self.run_test_reactions_to_over_bought_then_dip(START_PENDING_EVAL_NOTE, START_PENDING_EVAL_NOTE,
                                                        START_PENDING_EVAL_NOTE, -0.5,
                                                        -0.5, -0.5)
