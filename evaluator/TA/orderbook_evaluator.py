from evaluator.TA.TA_evaluator import OrderBookEvaluator


class WhalesOrderBookEvaluator(OrderBookEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def eval(self):
        pass
