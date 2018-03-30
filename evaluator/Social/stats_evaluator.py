from evaluator.Social.Social_evaluator import SocialEvaluator


class StatsEvaluator(SocialEvaluator):
    def __init__(self, config):
        super().__init__(config)


class GoogleTrendStatsEvaluator(StatsEvaluator):
    def __init__(self, config):
        super().__init__(config)
