import logging
import pprint
from abc import ABCMeta
from enum import Enum

from config.cst import CONFIG_ENABLED_OPTION, CONFIG_CATEGORY_NOTIFICATION, CONFIG_CATEGORY_SERVICES, CONFIG_GMAIL, \
    CONFIG_SERVICE_INSTANCE, CONFIG_TWITTER
from services import TwitterService
from services.gmail_service import GmailService
from trading import Exchange


class Notification:
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config
        self.notification_type = self.config[CONFIG_CATEGORY_NOTIFICATION]["type"]
        self.logger = logging.getLogger(self.__class__.__name__)

        # Debug
        if self.enabled():
            self.logger.debug("Enabled")
        else:
            self.logger.debug("Disabled")

    def enabled(self):
        if self.config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_ENABLED_OPTION]:
            return True
        else:
            return False

    def gmail_notification_available(self):
        if NotificationTypes.MAIL.value in self.notification_type:
            if GmailService.is_setup_correctly(self.config):
                return True
        return False

    def gmail_notification_factory(self, subject, mail):
        if self.gmail_notification_available():
            gmail_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][CONFIG_SERVICE_INSTANCE]
            result = gmail_service.send_mail(subject, mail)
            if result:
                self.logger.info("Mail sent")
        else:
            self.logger.debug("Mail disabled")

    def twitter_notification_available(self):
        if NotificationTypes.TWITTER.value in self.notification_type:
            if TwitterService.is_setup_correctly(self.config):
                return True
        return False

    def twitter_notification_factory(self, tweet):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = twitter_service.post(tweet)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None

    def twitter_response_factory(self, tweet_instance, tweet):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = twitter_service.respond(tweet_instance.id, tweet)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None


class EvaluatorNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.tweet_instance = None

    def notify_state_changed(self, final_eval, symbol_evaluator, trader, result, matrix):
        if self.gmail_notification_available():
            profitability, profitability_percent = trader.get_trades_manager().get_profitability()

            self.gmail_notification_factory("CRYPTO BOT ALERT : {0} / {1}".format(symbol_evaluator.crypto_currency,
                                                                                  result),
                                            "CRYPTO BOT ALERT : {0} / {1} \n {2} \n Current portfolio "
                                            "profitability : {3} "
                                            "{4} ({5}%)".format(
                                                symbol_evaluator.crypto_currency,
                                                result,
                                                pprint.pformat(matrix),
                                                round(profitability, 2),
                                                trader.get_trades_manager().get_reference_market(),
                                                round(profitability_percent, 2)))

        if self.twitter_notification_available():
            # + "\n see more at https://github.com/Trading-Bot/CryptoBot"
            formatted_pairs = [p.replace("/", "") for p in symbol_evaluator.get_symbol_pairs()]
            self.tweet_instance = self.twitter_notification_factory("CryptoBot ALERT : #{0} "
                                                                    "\n Cryptocurrency : #{1}"
                                                                    "\n Result : {2}"
                                                                    "\n Evaluation : {3}".format(
                symbol_evaluator.crypto_currency,
                " #".join(formatted_pairs),
                str(result).split(".")[1],
                final_eval))

        return self

    def get_tweet_instance(self):
        return self.tweet_instance


class OrdersNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.evaluator_notification = None

    def notify_create(self, evaluator_notification, orders, symbol):
        if evaluator_notification is not None:
            self.evaluator_notification = evaluator_notification

        if self.twitter_notification_available() \
                and evaluator_notification is not None \
                and evaluator_notification.get_tweet_instance() is not None:
            tweet_instance = evaluator_notification.get_tweet_instance()
            market, currency = Exchange.split_symbol(symbol)
            content = "Order creation "
            for order in orders:
                content += "\n {0} : {1} {2} at {3} {4}".format(order.get_order_type(),
                                                                round(order.get_origin_quantity(), 7),
                                                                currency,
                                                                round(order.get_origin_price(), 7),
                                                                market)
            self.twitter_response_factory(tweet_instance, content)

    def notify_end(self):
        pass


class NotificationTypes(Enum):
    MAIL = 1
    TWITTER = 2
