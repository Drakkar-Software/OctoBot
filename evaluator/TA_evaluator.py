from evaluator.evaluator import Evaluator


class TAEvaluator(Evaluator):
    def __init__(self):
        super().__init__()
        self.data = None

    def set_data(self, data):
        self.data = data
