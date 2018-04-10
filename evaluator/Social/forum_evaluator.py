from config.cst import *
from evaluator.Social.social_evaluator import ForumSocialEvaluator


class RedditForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        pass

    def run(self):
        pass

    def set_default_config(self):
        self.social_config = {
            CONFIG_REFRESH_RATE: 3
        }


class BTCTalkForumEvaluator(ForumSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        pass

    def run(self):
        pass
