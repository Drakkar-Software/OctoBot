from config.cst import EvaluatorClasses
from evaluator.TA_evaluator import OrderBookEvaluator


class WhalesOrderBookEvaluator(OrderBookEvaluator):
    def __init__(self):
        super().__init__()

    def eval(self):
        pass


class OrderBookEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            WhalesOrderBookEvaluator()
        ]
