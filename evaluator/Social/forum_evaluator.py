from config.cst import *
from evaluator.Social.social_evaluator import ForumSocialEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Util.text_analysis import TextAnalysis
from evaluator.Dispatchers.reddit_dispatcher import RedditDispatcher
from evaluator.Dispatchers.abstract_dispatcher import DispatcherAbstractClient
from tools.decoding_encoding import DecoderEncoder


class RedditForumEvaluator(ForumSocialEvaluator, DispatcherAbstractClient):
    def __init__(self):
        ForumSocialEvaluator.__init__(self)
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
        return RedditDispatcher

    def _print_entry(self, entry_text, count=""):
        self.logger.debug("Current note : {0} | {1} : {2} : Text : {3}".format(self.eval_note,
                                                                               count,
                                                                               self.symbol,
                                                                               DecoderEncoder.encode_into_bytes(
                                                                                   entry_text)))

    def receive_notification_data(self, data):
        self.count += 1
        self.eval_note = self._get_sentiment(data[CONFIG_REDDIT_ENTRY])
        if self.eval_note != START_PENDING_EVAL_NOTE:
            self._print_entry(data[CONFIG_REDDIT_ENTRY].selftext, str(self.count))
        self._check_eval_note()

    def _check_eval_note(self):
        if self.eval_note != START_PENDING_EVAL_NOTE:
            if self.eval_note > 0.85 or self.eval_note < -0.85:
                self.notify_evaluator_thread_managers(self.__class__.__name__)

    def _get_sentiment(self, entry):
        reddit_entry_min_length = 1
        if entry.selftext and len(entry.selftext) > reddit_entry_min_length:
            return -1 * self.sentiment_analyser.analyse(entry.selftext)
        return START_PENDING_EVAL_NOTE

    def is_interested_by_this_notification(self, subreddit_name):
        # true if in this symbol's subreddits configuration
        if self.social_config[CONFIG_REDDIT_SUBREDDITS]:
            for subreddit in self.social_config[CONFIG_REDDIT_SUBREDDITS][self.symbol]:
                if subreddit.lower() == subreddit_name:
                    return True
        return False

    def _purify_config(self):
        # remove other symbols data to avoid unnecessary entries
        if CONFIG_REDDIT_SUBREDDITS in self.social_config \
                and self.symbol in self.social_config[CONFIG_REDDIT_SUBREDDITS]:
            self.social_config[CONFIG_REDDIT_SUBREDDITS] = \
                {self.symbol: self.social_config[CONFIG_REDDIT_SUBREDDITS][self.symbol]}
        else:
            self.social_config[CONFIG_REDDIT_SUBREDDITS] = {}

    def prepare(self):
        self._purify_config()
        self.sentiment_analyser = AdvancedManager.get_util_instance(self.config, TextAnalysis)

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
        self.is_threaded = False

    def get_data(self):
        pass

    def eval_impl(self):
        pass

    def run(self):
        pass
