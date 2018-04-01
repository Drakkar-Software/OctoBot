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

    def notify(self, timeframe, symbol, eval):
        if self.notification_type == NotificationTypes.MAIL.value:
            mail = GmailMailSendFactory(self.config)
            mail.set_to(self.config["notification"]["mail_dest"])
            mail.set_subject("CRYPTO BOT ALERT : " + str(timeframe) + " / " + symbol + " / " + str(eval))
            mail.set_content("CRYPTO BOT ALERT : " + str(timeframe) + " / " + symbol + " / " + str(eval))
            mail.send()
            self.logger.info("Mail sent")


class NotificationTypes(Enum):
    MAIL = 1
