from evaluator.Social.Social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass
