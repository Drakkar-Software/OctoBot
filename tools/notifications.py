import logging
from enum import Enum

from config.cst import CONFIG_ENABLED_OPTION, CONFIG_CATEGORY_NOTIFICATION, CONFIG_CATEGORY_SERVICES, CONFIG_GMAIL, \
    CONFIG_SERVICE_INSTANCE, CONFIG_TWITTER
from services import TwitterService
from services.gmail_service import GmailService


class Notification:
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

    def notify(self, final_eval, symbol_evaluator, trader, result, matrix):
        if NotificationTypes.MAIL.value in self.notification_type:
            if GmailService.is_setup_correctly(self.config):
                gmail_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][CONFIG_SERVICE_INSTANCE]

                profitability, profitability_percent = trader.get_trades_manager().get_profitability()

                gmail_service.send_mail("CRYPTO BOT ALERT : {0} / {1}".format(symbol_evaluator.crypto_currency,
                                                                              result),
                                        "CRYPTO BOT ALERT : {0} / {1} \n {2} \n Current portfolio profitability : {3} "
                                        "{4} ({5}%)".format(
                                            symbol_evaluator.crypto_currency,
                                            result,
                                            matrix,
                                            round(profitability, 2),
                                            trader.get_trades_manager().get_reference_market(),
                                            round(profitability_percent, 2)))

                self.logger.info("Mail sent")
            else:
                self.logger.debug("Mail disabled")

        if NotificationTypes.TWITTER.value in self.notification_type:
            if TwitterService.is_setup_correctly(self.config):
                twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]

                # + "\n see more at https://github.com/Trading-Bot/CryptoBot"
                formatted_pairs = [p.replace("/", "") for p in symbol_evaluator.get_symbol_pairs()]
                twitter_service.post("CryptoBot ALERT : #{0} "
                                     "\n Cryptocurrency : #{1}"
                                     "\n Result : {2}"
                                     "\n Evaluation : {3}".format(
                    symbol_evaluator.crypto_currency,
                    " #".join(formatted_pairs),
                    str(result).split(".")[1],
                    final_eval))

                self.logger.info("Twitter sent")
            else:
                self.logger.debug("Twitter notification disabled")


class NotificationTypes(Enum):
    MAIL = 1
    TWITTER = 2
