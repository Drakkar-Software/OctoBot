from config.cst import *
from evaluator.Social.social_evaluator import NewsSocialEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Util.text_analysis import TextAnalysis
from evaluator.Dispatchers.twitter_dispatcher import TwitterDispatcher
from evaluator.Dispatchers.abstract_dispatcher import DispatcherAbstractClient
from tools.decoding_encoding import DecoderEncoder


class TwitterNewsEvaluator(NewsSocialEvaluator, DispatcherAbstractClient):
    def __init__(self):
        NewsSocialEvaluator.__init__(self)
        DispatcherAbstractClient.__init__(self)
        self.is_threaded = False
        self.count = 0
        self.symbol = ""
        self.sentiment_analyser = None
        self.is_self_refreshing = True

    def set_dispatcher(self, dispatcher):
        super().set_dispatcher(dispatcher)
        self.dispatcher.update_social_config(self.social_config)

    @staticmethod
    def get_dispatcher_class():
        return TwitterDispatcher

    def get_twitter_service(self):
        return self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]

    def _print_tweet(self, tweet_text, count=""):
        self.logger.debug("Current note : {0} | {1} : {2} : Text : {3}".format(self.eval_note,
                                                                               count,
                                                                               self.symbol,
                                                                               DecoderEncoder.encode_into_bytes(
                                                                                   tweet_text)))

    def receive_notification_data(self, data):
        self.count += 1
        self.eval_note = self.get_tweet_sentiment(data[CONFIG_TWEET], data[CONFIG_TWEET_DESCRIPTION])
        if self.eval_note != START_PENDING_EVAL_NOTE:
            self._print_tweet(data[CONFIG_TWEET_DESCRIPTION], str(self.count))
        self._check_eval_note()

    def _check_eval_note(self):
        if self.eval_note != START_PENDING_EVAL_NOTE:
            if self.eval_note > 0.6 or self.eval_note < -0.6:
                self.notify_evaluator_thread_managers(self.__class__.__name__)

    def get_tweet_sentiment(self, tweet, tweet_text, is_a_quote=False):
        try:
            if is_a_quote:
                return -1 * self.sentiment_analyser.analyse(tweet_text)
            else:
                stupid_useless_name = "########"
                author_screen_name = tweet['user']['screen_name'] if "screen_name" in tweet['user'] else stupid_useless_name
                author_name = tweet['user']['name'] if "name" in tweet['user'] else stupid_useless_name
                if self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
                    if author_screen_name in self.social_config[CONFIG_TWITTERS_ACCOUNTS][self.symbol] \
                       or author_name in self.social_config[CONFIG_TWITTERS_ACCOUNTS][self.symbol]:
                        return -1 * self.sentiment_analyser.analyse(tweet_text)
        except KeyError:
            pass

        # ignore # for the moment (too much of bullshit)
        return START_PENDING_EVAL_NOTE

    def is_interested_by_this_notification(self, notification_description):
        # true if in twitter accounts
        if self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
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
        if self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            for hashtags in self.social_config[CONFIG_TWITTERS_HASHTAGS][self.symbol]:
                if hashtags.lower() in notification_description:
                    return True
            return False

    def _purify_config(self):
        # remove other symbols data to avoid unnecessary tweets
        if CONFIG_TWITTERS_ACCOUNTS in self.social_config \
                and self.symbol in self.social_config[CONFIG_TWITTERS_ACCOUNTS]:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = \
                {self.symbol: self.social_config[CONFIG_TWITTERS_ACCOUNTS][self.symbol]}
        else:
            self.social_config[CONFIG_TWITTERS_ACCOUNTS] = {}
        if CONFIG_TWITTERS_HASHTAGS in self.social_config \
                and self.symbol in self.social_config[CONFIG_TWITTERS_HASHTAGS]:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = \
                {self.symbol: self.social_config[CONFIG_TWITTERS_HASHTAGS][self.symbol]}
        else:
            self.social_config[CONFIG_TWITTERS_HASHTAGS] = {}

    def prepare(self):
        self._purify_config()
        self.sentiment_analyser = AdvancedManager.get_util_instance(self.config, TextAnalysis)

    def get_data(self):
        pass

    def eval_impl(self):
        pass

    def run(self):
        pass


class MediumNewsEvaluator(NewsSocialEvaluator):
    def __init__(self):
        super().__init__()
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        self.notify_evaluator_thread_managers(self.__class__.__name__)

    def run(self):
        pass

    def set_default_config(self):
        self.social_config = {
            CONFIG_REFRESH_RATE: 2
        }
