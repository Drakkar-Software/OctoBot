from abc import ABCMeta, abstractmethod
from enum import Enum

from evaluator.TA.momentum_evaluator import *
from evaluator.TA.orderbook_evaluator import *
from evaluator.TA.trend_evaluator import *
from evaluator.TA.volatility_evaluator import *


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


class TAEvaluatorClasses(Enum):
    OBVMomentumEvaluator()
    RSIMomentumEvaluator()
    WhalesOrderBookEvaluator()
    ADXMomentumEvaluator()
    BBVolatilityEvaluator()
