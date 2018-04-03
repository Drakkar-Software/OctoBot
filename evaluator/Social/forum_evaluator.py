from evaluator.Social.social_evaluator import ForumSocialEvaluator


class RedditForumEvaluator(ForumSocialEvaluator):
    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass


class BTCTalkForumEvaluator(ForumSocialEvaluator):
    def __init__(self, evaluation_matrix, evaluator_thread):
        super().__init__(evaluation_matrix, evaluator_thread)
        self.enabled = False

    def get_data(self):
        pass

    def eval(self):
        pass
