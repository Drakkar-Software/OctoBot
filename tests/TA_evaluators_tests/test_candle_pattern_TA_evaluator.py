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
