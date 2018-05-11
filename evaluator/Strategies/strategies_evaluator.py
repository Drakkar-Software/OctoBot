from abc import *

from evaluator.abstract_evaluator import AbstractEvaluator
from tools.evaluator_divergence_analyser import EvaluatorDivergenceAnalyser


class StrategiesEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.matrix = None
        self.divergence_evaluator_analyser = None

    def set_matrix(self, matrix):
        self.matrix = matrix.get_matrix()

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.matrix is None)

    def create_divergence_analyser(self):
        self.divergence_evaluator_analyser = EvaluatorDivergenceAnalyser()

    def get_divergence(self):
        return self.divergence_evaluator_analyser.update(self.matrix)

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


class MixedStrategiesEvaluator(StrategiesEvaluator):
    __metaclass__ = StrategiesEvaluator

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")
