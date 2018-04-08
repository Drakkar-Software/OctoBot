from abc import *

from evaluator.abstract_evaluator import AbstractEvaluator


class strategiesEvaluator(AbstractEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.matrix = None

    def set_matrix(self, matrix):
        self.matrix = matrix.get_matrix()

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.matrix is None)

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


class MixedstrategiesEvaluator(strategiesEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")