from config.cst import *
from evaluator.Social.social_evaluator import ForumSocialEvaluator
from evaluator.Util.advanced_manager import AdvancedManager
from evaluator.Util.text_analysis import TextAnalysis
from evaluator.Util.overall_state_analysis import OverallStateAnalyser
from evaluator.Dispatchers.reddit_dispatcher import RedditDispatcher
from evaluator.Dispatchers.abstract_dispatcher import DispatcherAbstractClient


# RedditForumEvaluator is used to get an overall state of a market, it will not trigger a trade
# (notify its evaluators) but is used to measure hype and trend of a market.
class RedditForumEvaluator(ForumSocialEvaluator, DispatcherAbstractClient):
    def __init__(self):
        ForumSocialEvaluator.__init__(self)
        DispatcherAbstractClient.__init__(self)
        self.overall_state_analyser = OverallStateAnalyser()
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

    def _print_entry(self, entry_text, entry_note, count=""):
        self.logger.debug("New reddit entry ! : {0} | {1} : {2} : Link : {3}".format(entry_note,
                                                                                     count,
                                                                                     self.symbol,
                                                                                     entry_text))

    def receive_notification_data(self, data):
        self.count += 1
        entry_note = self._get_sentiment(data[CONFIG_REDDIT_ENTRY])
        if entry_note != START_PENDING_EVAL_NOTE:
            self.overall_state_analyser.add_evaluation(entry_note, data[CONFIG_REDDIT_ENTRY_WEIGHT], False)
            if data[CONFIG_REDDIT_ENTRY_WEIGHT] > 4:
                link = "https://www.reddit.com{0}".format(data[CONFIG_REDDIT_ENTRY].permalink)
                self._print_entry(link, entry_note, str(self.count))

    # overwrite get_eval_note from abstract evaluator to recompute OverallStateAnalyser evaluation
    def get_eval_note(self):
        self.eval_note = self.overall_state_analyser.get_overall_state_after_refresh()
        return self.eval_note

    def _get_sentiment(self, entry):
        # analysis entry text and gives overall sentiment
        reddit_entry_min_length = 50
        # ignore usless (very short) entries
        if entry.selftext and len(entry.selftext) >= reddit_entry_min_length:
            return -1 * self.sentiment_analyser.analyse(entry.selftext)
        return START_PENDING_EVAL_NOTE

    def is_interested_by_this_notification(self, notification_description):
        # true if in this symbol's subreddits configuration
        if self.social_config[CONFIG_REDDIT_SUBREDDITS]:
            for subreddit in self.social_config[CONFIG_REDDIT_SUBREDDITS][self.symbol]:
                if subreddit.lower() == notification_description:
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
