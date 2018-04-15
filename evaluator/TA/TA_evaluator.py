from abc import *

from config.cst import START_PENDING_EVAL_NOTE, INIT_EVAL_NOTE
from evaluator.abstract_evaluator import AbstractEvaluator


class TAEvaluator(AbstractEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.data = None
        self.short_term_averages = [7, 5, 4, 3, 2, 1]
        self.long_term_averages = [40, 30, 20, 15, 10]

    def set_data(self, data):
        self.data = data

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.data is None)

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")


class MomentumEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class OrderBookEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class VolatilityEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class TrendEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")
