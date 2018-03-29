from evaluator.evaluator import Evaluator


class TAEvaluator(Evaluator):
    def __init__(self, config, data):
        super().__init__(config)
        self.data = data
