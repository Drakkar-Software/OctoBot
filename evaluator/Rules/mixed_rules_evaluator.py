from config.cst import *
from evaluator.RealTime import InstantFluctuationsEvaluator
from evaluator.Rules import MixedRulesEvaluator
from evaluator.Social import MediumNewsEvaluator, RedditForumEvaluator


class InstantSocialReactionMixedRulesEvaluator(MixedRulesEvaluator):
    def __init__(self):
        super().__init__()

        self.social_counter = 0
        self.instant_counter = 0

        self.instant_evaluation = 0
        self.social_evaluation = 0

    def eval_impl(self) -> None:
        # TODO : This is an example
        if InstantFluctuationsEvaluator.get_name() in self.matrix[EvaluatorMatrixTypes.REAL_TIME]:
            self.instant_evaluation += self.matrix[EvaluatorMatrixTypes.REAL_TIME][
                InstantFluctuationsEvaluator.get_name()]
            self.inc_instant_counter()

        if MediumNewsEvaluator.get_name() in self.matrix[EvaluatorMatrixTypes.SOCIAL]:
            self.social_evaluation += self.matrix[EvaluatorMatrixTypes.SOCIAL][MediumNewsEvaluator.get_name()]
            self.inc_social_counter()

        if RedditForumEvaluator.get_name() in self.matrix[EvaluatorMatrixTypes.SOCIAL]:
            self.social_evaluation += self.matrix[EvaluatorMatrixTypes.SOCIAL][MediumNewsEvaluator.get_name()]
            self.inc_social_counter()

        self.finalize()

    def inc_social_counter(self, inc=1):
        self.social_counter += inc

    def inc_instant_counter(self, inc=1):
        self.instant_counter += inc

    def finalize(self):
        # TODO : This is an example
        eval_temp = 0
        category = 0

        if self.instant_counter > 0:
            eval_temp += self.instant_evaluation / self.instant_counter
            category += 1

        if self.social_counter > 0:
            eval_temp += self.social_evaluation / self.social_counter
            category += 1

        if category > 0:
            self.eval_note = eval_temp / category
