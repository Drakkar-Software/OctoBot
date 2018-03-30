from evaluator.Social.Social_evaluator import SocialEvaluator


class NewsEvaluator(SocialEvaluator):
    def __init__(self, config):
        super().__init__(config)


class TwitterNewsEvaluator(NewsEvaluator):
    def __init__(self, config):
        super().__init__(config)


class MediumNewsEvaluator(NewsEvaluator):
    def __init__(self, config):
        super().__init__(config)
