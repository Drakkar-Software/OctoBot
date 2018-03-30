from abc import ABCMeta, abstractmethod
from enum import Enum

from evaluator.Social.forum_evaluator import *
from evaluator.Social.news_evaluator import *
from evaluator.Social.stats_evaluator import *


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

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class StatsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class ForumSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class NewsSocialEvaluator(SocialEvaluator):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()

    @abstractmethod
    def _eval(self):
        raise NotImplementedError("Eval not implemented")


class SocialEvaluatorClasses(Enum):
    # TwitterNewsEvaluator()
    # MediumNewsEvaluator()
    # RedditForumEvaluator()
    # BTCTalkForumEvaluator()
    GoogleTrendStatsEvaluator()
