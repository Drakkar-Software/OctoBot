from abc import *

from evaluator.abstract_evaluator import AbstractEvaluator


class RulesEvaluator(AbstractEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


