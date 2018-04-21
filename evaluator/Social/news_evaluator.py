from config.cst import *
from evaluator.Dispatchers.TwitterDispatcher import TwitterDispatcher
from evaluator.Social.social_evaluator import NewsSocialEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Util.sentiment_analyser import SentimentAnalyser
from evaluator.evaluator_dispatcher import *
from tools.decoding_encoding import DecoderEncoder


class TwitterNewsEvaluator(NewsSocialEvaluator, EvaluatorDispatcherClient):
    def __init__(self):
        NewsSocialEvaluator.__init__(self)
        EvaluatorDispatcherClient.__init__(self)
        self.enabled = True
        self.is_threaded = False
        self.count = 0
        self.symbol = ""
        self.sentiment_analyser = None

    def set_dispatcher(self, dispatcher):
        super().set_dispatcher(dispatcher)
        self.dispatcher.update_social_config(self.social_config)

    def get_data(self):
        pass

    @staticmethod
    def get_dispatcher_class():
        return TwitterDispatcher

    def get_twitter_service(self):
        return self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]

    def _print_tweet(self, tweet, count):
        self.set_eval_note(self._get_sentiment(tweet))
        self._check_eval_note()
        self.logger.debug("Current note : " + str(self.eval_note) + "|"
                          + str(count) + " : " + str(self.symbol) + " : " + "Text : "
                          + str(DecoderEncoder.encode_into_bytes(tweet)))

    def receive_notification_data(self, data):
        self.count += 1
        self._print_tweet(data[CONFIG_TWEET_DESCRIPTION], self.count)

    def _check_eval_note(self):
        if self.eval_note > 0.8 or self.eval_note < -0.8:
            self.notify_evaluator_threads(self.__class__.__name__)

    def _get_sentiment(self, tweet):
        # The compound score is computed by summing the valence scores of each word in the lexicon, adjusted according
        # to the rules, and then normalized to be between -1 (most extreme negative) and +1 (most extreme positive).
        # https://github.com/cjhutto/vaderSentiment
        return -0.1*self.sentiment_analyser.analyse(tweet)["compound"]

    def eval_impl(self):
        pass

    def run(self):
        pass

    def is_interested_by_this_notification(self, notification_description):
        # true if in twitter accounts
        for account in self.social_config[CONFIG_TWITTERS_ACCOUNTS][self.symbol]:
            if account.lower() in notification_description:
                return True

        # false if it's a RT of an unfollowed account
        if notification_description.startswith("rt"):
            return False

        # true if contains symbol
        if self.symbol.lower() in notification_description:
            return True

        # true if in hashtags
        for hashtags in self.social_config[CONFIG_TWITTERS_HASHTAGS][self.symbol]:
            if hashtags.lower() in notification_description:
                return True
        return False

    def _purify_config(self):
        # remove other symbols data to avoid unnecessary tweets
        if self.symbol in self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = \
                {self.symbol: self.social_config[CONFIG_TWITTERS_ACCOUNTS][self.symbol]}
        else:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = {}
        if self.symbol in self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = \
                {self.symbol: self.social_config[CONFIG_TWITTERS_HASHTAGS][self.symbol]}
        else:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = {}

    def prepare(self):
        self._purify_config()
        self.sentiment_analyser = AdvancedManager.get_util_instance(self.config, SentimentAnalyser)


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
