from abc import *

from config.cst import *


class TAEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.data = None
        self.config = None
        self.eval_note = START_EVAL_NOTE
        self.ponderation = START_EVAL_PONDERATION
        self.logger = None

    def set_data(self, data):
        self.data = data

    def set_config(self, config):
        self.config = config

    def get_eval_note(self):
        return self.eval_note

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")


class MomentumEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")


class OrderBookEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")


class VolatilityEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")


class TrendEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def eval(self):
        raise NotImplementedError("Eval not implemented")
