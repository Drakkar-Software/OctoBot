import logging
from enum import Enum

from botcore.services.mail.send_gmail import GmailMailSendFactory


class Notification:
    def __init__(self, config):
        self.config = config
        self.notification_type = self.config["notification"]["type"]
        self.logger = logging.getLogger("Notifier")

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

    def notify(self, symbol, result, matrix):
        if self.notification_type == NotificationTypes.MAIL.value:
            # if config contains enough data for mailing
            if self.mail_enabled():
                mail = GmailMailSendFactory(self.config)
                mail.set_to(self.config["service"]["mail"]["mail_dest"])
                mail.set_subject("CRYPTO BOT ALERT : " + symbol + " / " + str(result))
                mail.set_content("CRYPTO BOT ALERT : " + symbol + " / " + str(result) + "\n MATRIX : " + str(matrix))
                mail.send()
                self.logger.info("Mail sent")
            else:
                self.logger.debug("Mail disabled")

    def mail_enabled(self):
        if self.service_enabled() and "mail" in self.config["service"]:
            return True
        else:
            return False

    def service_enabled(self):
        if "service" in self.config:
            return True
        else:
            return False


class NotificationTypes(Enum):
    MAIL = 1
