import time
from abc import *
from config.cst import MAX_TA_EVAL_TIME_SECONDS
from evaluator.abstract_evaluator import AbstractEvaluator


class TAEvaluator(AbstractEvaluator):
    __metaclass__ = AbstractEvaluator

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

    def eval(self) -> None:
        self.is_updating = True
        start_time = time.time()
        super().eval()
        execution_time = time.time()-start_time
        if execution_time > MAX_TA_EVAL_TIME_SECONDS:
            self.logger.warning("for {0} took longer than expected: {1} seconds.".format(self.symbol,
                                                                                         execution_time))


class MomentumEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class OrderBookEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class VolatilityEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")


class TrendEvaluator(TAEvaluator):
    __metaclass__ = TAEvaluator

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval_impl(self):
        raise NotImplementedError("Eval_impl not implemented")
