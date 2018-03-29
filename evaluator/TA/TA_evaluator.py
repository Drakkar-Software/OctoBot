from evaluator.evaluator import Evaluator


class TAEvaluator(Evaluator):
    def __init__(self, symbol, time_frame):
        super().__init__()
        self.symbol = symbol
        self.time_frame = time_frame
