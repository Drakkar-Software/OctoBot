import logging
from enum import Enum

from botcore.services.mail.send_gmail import GmailMailSendFactory
from botcore.social.twitter.post import TwitterPostFactory


class Notification:
    def __init__(self, config):
        self.config = config
        self.notification_type = self.config["notification"]["type"]
        self.logger = logging.getLogger(self.__class__.__name__)

        # Debug
        if self.enabled():
            self.logger.debug("Enabled")
        else:
            self.logger.debug("Disabled")

    def enabled(self):
        if self.config["notification"]["enabled"]:
            return True
        else:
            return False

    def notify(self, final_eval, symbol_evaluator, result, matrix):
        if NotificationTypes.MAIL.value in self.notification_type:
            # if config contains enough data for mailing
            if self.mail_enabled():
                mail = GmailMailSendFactory(self.config)
                mail.set_to(self.config["services"]["mail"]["mail_dest"])
                mail.set_subject("CRYPTO BOT ALERT : " + symbol_evaluator.crypto_currency + " / " + str(result))
                mail.set_content("CRYPTO BOT ALERT : " + symbol_evaluator.crypto_currency + " / " + str(result)
                                 + "\n MATRIX : " + str(matrix))
                mail.send()
                self.logger.info("Mail sent")
            else:
                self.logger.debug("Mail disabled")

        if NotificationTypes.TWITTER.value in self.notification_type:
            # if config contains enough data for twitting
            if self.twitter_enabled():
                twitter = TwitterPostFactory(self.config)

                # + "\n see more at https://github.com/Trading-Bot/CryptoBot"
                formatted_pairs = [p.replace("/", "") for p in symbol_evaluator.get_symbol_pairs()]
                twitter.set_content("CryptoBot ALERT : #" + symbol_evaluator.crypto_currency
                                    + "\n Cryptocurrency : #" + " #".join(formatted_pairs)
                                    + "\n Result : " + str(result).split(".")[1]
                                    + "\n Evaluation : " + str(final_eval))
                twitter.upload_post()
                self.logger.info("Twitter sent")
            else:
                self.logger.debug("Twitter notification disabled")

    def twitter_enabled(self):
        if self.services_enabled() and "twitter" in self.config["services"]:
            return True
        else:
            return False

    def mail_enabled(self):
        if self.services_enabled() and "mail" in self.config["services"]:
            return True
        else:
            return False

    def services_enabled(self):
        if "services" in self.config:
            return True
        else:
            return False


class NotificationTypes(Enum):
    MAIL = 1
    TWITTER = 2
