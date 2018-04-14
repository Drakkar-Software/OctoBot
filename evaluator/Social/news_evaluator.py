from random import randint

from config.cst import *
from evaluator.Dispatchers.TwitterDispatcher import TwitterDispatcher
from evaluator.Social.social_evaluator import NewsSocialEvaluator
from evaluator.evaluator_dispatcher import *


class TwitterNewsEvaluator(NewsSocialEvaluator, EvaluatorDispatcherClient):
    def __init__(self):
        NewsSocialEvaluator.__init__(self)
        EvaluatorDispatcherClient.__init__(self)
        self.enabled = True
        self.is_threaded = False
        self.count = 0
        self.symbol = ""

    def set_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher
        self.dispatcher.set_social_config(self.social_config)

    def get_data(self):
        pass

    @staticmethod
    def get_dispatcher_class():
        return TwitterDispatcher

    def print_tweet(self, tweet, count):
        twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
        self.logger.debug(twitter_service.tweet_to_string(tweet, count))

    def receive_notification_data(self, data):
        self.count += 1
        self.print_tweet(data[CONFIG_TWEET], self.count)

    def eval_impl(self):
        v = randint(0, 100)
        if v > 95:
            self.notify_evaluator_threads(self.__class__.__name__)

    def run(self):
        pass


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.enabled = False
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        self.notify_evaluator_threads(self.__class__.__name__)

    def run(self):
        pass

    def set_default_config(self):
        self.social_config = {
            CONFIG_REFRESH_RATE: 2
        }
