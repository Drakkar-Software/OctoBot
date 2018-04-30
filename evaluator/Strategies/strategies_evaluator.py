from abc import *

import math

from config.cst import START_PENDING_EVAL_NOTE
from evaluator.abstract_evaluator import AbstractEvaluator


class StrategiesEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

    def __init__(self):
        super().__init__()
        self.matrix = None

    def set_matrix(self, matrix):
        self.matrix = matrix.get_matrix()

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.matrix is None)

    @staticmethod
    def check_valid_eval_note(eval_note):
        if eval_note and eval_note is not START_PENDING_EVAL_NOTE and not math.isnan(eval_note):
            return True
        else:
            return False

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