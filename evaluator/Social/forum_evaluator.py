from evaluator.Social.Social_evaluator import SocialEvaluator


class ForumEvaluator(SocialEvaluator):
    def __init__(self, config):
        super().__init__(config)


class RedditForumEvaluator(ForumEvaluator):
    def __init__(self, config):
        super().__init__(config)


class BTCTalkForumEvaluator(ForumEvaluator):
    def __init__(self, config):
        super().__init__(config)
