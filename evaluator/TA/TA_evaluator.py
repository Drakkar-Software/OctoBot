from abc import *

from config.cst import *
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

    def set_eval_note(self, new_eval_note):
        if self.eval_note + new_eval_note > 1:
            self.eval_note = 1
        elif self.eval_note + new_eval_note < -1:
            self.eval_note = -1
        else:
            self.eval_note += new_eval_note

    def get_is_evaluable(self):
        return not (self.get_is_updating() or self.data is None)

    @abstractmethod
    def eval_impl(self) -> None:
        raise NotImplementedError("Eval_impl not implemented")

    # trend < 0 --> Down trend
    # trend > 0 --> Up trend
    @staticmethod
    def get_trend(data_frame, averages_to_use):
        trend = 0
        inc = round(1/len(averages_to_use), 2)
        averages = []

        # Get averages
        for average_to_use in averages_to_use:
            averages.append(data_frame.tail(average_to_use).values.mean())

        for a in range(0, len(averages) - 1):
            if averages[a] - averages[a+1] > 0:
                trend -= inc
            else:
                trend += inc

        return trend


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
