import numpy

from evaluator.Util.abstract_util import AbstractUtil
from config.cst import START_PENDING_EVAL_NOTE


class OverallStateAnalyser(AbstractUtil):
    def __init__(self):
        self.overall_state = START_PENDING_EVAL_NOTE
        self.evaluation_count = 0
        self.evaluations = []

    # evaluation: number between -1 and 1
    # weight: integer between 0 (not even taken into account) and X
    def add_evaluation(self, evaluation, weight, refresh_overall_state=True):
        self.evaluations.append(StateEvaluation(evaluation, weight))
        if refresh_overall_state:
            self._refresh_overall_state()

    def get_overall_state_after_refresh(self, refresh_overall_state=True):
        if refresh_overall_state:
            self._refresh_overall_state()
        return self.overall_state

    # computes self.overall_state using self.evaluations values and weights
    def _refresh_overall_state(self):
        if self.evaluations:
            self.overall_state = numpy.mean(
                [evaluation.value for evaluation in self.evaluations for _ in range(evaluation.weight)]
            )


class StateEvaluation:
    def __init__(self, value, weight):
        self.value = value
        self.weight = weight
