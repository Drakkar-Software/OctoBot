from evaluator.Social.social_evaluator import ForumSocialEvaluator


class RedditForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = False

    def get_data(self):
        pass

    def eval(self):
        pass


class BTCTalkForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = False

    def get_data(self):
        pass

    def eval(self):
        pass
