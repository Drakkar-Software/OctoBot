from config.cst import EvaluatorClasses
from evaluator.Social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()

    def get_data(self):
        pass

    def eval(self):
        pass


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()

    def get_data(self):
        pass

    def eval(self):
        pass


class NewsSocialEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            MediumNewsEvaluator(),
            TwitterNewsEvaluator()
        ]
