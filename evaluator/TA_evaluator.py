from abc import *


class TAEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.data = None
        self.config = None

    def set_data(self, data):
        self.data = data

    def set_config(self, config):
        self.config = config

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class MomentumEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class OrderBookEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class VolatilityEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class TrendEvaluator(TAEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")
