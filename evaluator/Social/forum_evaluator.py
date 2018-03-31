from config.cst import EvaluatorClasses
from evaluator.Social_evaluator import ForumSocialEvaluator


class RedditForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()

    def get_data(self):
        pass

    def eval(self):
        pass


class BTCTalkForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()

    def get_data(self):
        pass

    def eval(self):
        pass


class ForumSocialEvaluatorClasses(EvaluatorClasses):
    def __init__(self):
        super().__init__()
        self.classes = [
            RedditForumEvaluator(),
            BTCTalkForumEvaluator(),
        ]
