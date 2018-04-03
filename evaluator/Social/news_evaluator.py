from evaluator.Social.social_evaluator import NewsSocialEvaluator


class TwitterNewsEvaluator(NewsSocialEvaluator):
    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass
