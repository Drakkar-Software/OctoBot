from config.cst import *
from evaluator.RealTime import InstantFluctuationsEvaluator
from evaluator.Strategies import MixedStrategiesEvaluator
from evaluator.Social import MediumNewsEvaluator, RedditForumEvaluator


# TEMP strategy
class TempFullMixedStrategiesEvaluator(MixedStrategiesEvaluator):
    def __init__(self):
        super().__init__()
        self.social_counter = 0
        self.ta_relevance_counter = 0
        self.rt_counter = 0

        self.ta_evaluation = 0
        self.social_evaluation = 0
        self.rt_evaluation = 0

    def inc_social_counter(self, inc=1):
        self.social_counter += inc

    def inc_ta_counter(self, inc=1):
        self.ta_relevance_counter += inc

    def inc_rt_counter(self, inc=1):
        self.rt_counter += inc

    @staticmethod
    def check_valid_eval_note(eval_note):
        if eval_note and eval_note is not START_PENDING_EVAL_NOTE:
            return True
        else:
            return False

    def eval_impl(self) -> None:
        # TODO : temp counter without relevance
        self.social_counter = 0
        self.rt_counter = 0

        # relevance counters
        self.ta_relevance_counter = 0

        # eval note total with relevance factor
        self.ta_evaluation = 0
        self.social_evaluation = 0
        self.rt_evaluation = 0

        for rt in self.matrix[EvaluatorMatrixTypes.REAL_TIME]:
            if self.check_valid_eval_note(self.matrix[EvaluatorMatrixTypes.REAL_TIME][rt]):
                    self.rt_evaluation += self.matrix[EvaluatorMatrixTypes.REAL_TIME][rt]
                    self.inc_rt_counter()

        for ta in self.matrix[EvaluatorMatrixTypes.TA]:
            if self.matrix[EvaluatorMatrixTypes.TA][ta]:
                for ta_time_frame in self.matrix[EvaluatorMatrixTypes.TA][ta]:
                    if self.check_valid_eval_note(self.matrix[EvaluatorMatrixTypes.TA][ta][ta_time_frame]):
                        time_frame_relevance = TimeFramesRelevance[ta_time_frame]
                        self.ta_evaluation += self.matrix[EvaluatorMatrixTypes.TA][ta][ta_time_frame] * time_frame_relevance
                        self.inc_ta_counter(time_frame_relevance)

        for social in self.matrix[EvaluatorMatrixTypes.SOCIAL]:
            if self.check_valid_eval_note(self.matrix[EvaluatorMatrixTypes.SOCIAL][social]):
                self.social_evaluation += self.matrix[EvaluatorMatrixTypes.SOCIAL][social]
                self.inc_social_counter()

        self.finalize()

    def finalize(self):
        # TODO : This is an example
        eval_temp = 0
        category = 0

        if self.ta_relevance_counter > 0:
            eval_temp += self.ta_evaluation / self.ta_relevance_counter
            category += 1

        if self.social_counter > 0:
            eval_temp += self.social_evaluation / self.social_counter
            category += 1

        if self.rt_counter > 0:
            eval_temp += self.rt_evaluation / self.rt_counter
            category += 1

        if category > 0:
            self.eval_note = eval_temp / category


class InstantSocialReactionMixedStrategiesEvaluator(MixedStrategiesEvaluator):
    def __init__(self):
        super().__init__()
        self.social_counter = 0
        self.instant_counter = 0

        self.instant_evaluation = 0
        self.social_evaluation = 0

    def eval_impl(self) -> None:
        self.social_counter = 0
        self.instant_counter = 0

        self.instant_evaluation = 0
        self.social_evaluation = 0

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
