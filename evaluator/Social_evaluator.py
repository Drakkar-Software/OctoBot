from abc import ABCMeta


class SocialEvaluator:
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.symbol = None
        self.history_time = None
        self.config = None

    def set_symbol(self, symbol):
        self.symbol = symbol

    def set_history_time(self, history_time):
        self.history_time = history_time

    def set_config(self, config):
        self.config = config


class StatsEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()


class ForumEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()


class NewsEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
