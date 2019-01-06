#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
import pprint
from abc import ABCMeta
from enum import Enum

from config import CONFIG_CATEGORY_NOTIFICATION, CONFIG_CATEGORY_SERVICES, CONFIG_GMAIL, \
    CONFIG_SERVICE_INSTANCE, CONFIG_TWITTER, CONFIG_TELEGRAM, CONFIG_NOTIFICATION_PRICE_ALERTS, \
    CONFIG_NOTIFICATION_TRADES, CONFIG_NOTIFICATION_TYPE
from interfaces.web import add_notification
from services import TwitterService, TelegramService, WebService
from services.gmail_service import GmailService
from tools.pretty_printer import PrettyPrinter
from trading.trader.trades_manager import TradesManager


class Notification:
    __metaclass__ = ABCMeta

    def __init__(self, config):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self.notification_type = self.config[CONFIG_CATEGORY_NOTIFICATION][CONFIG_NOTIFICATION_TYPE]
        self._enable = self.config[CONFIG_CATEGORY_NOTIFICATION]

    # return True if key is enabled
    # if key is not given, return True if at least one key is enabled
    def enabled(self, key=None):
        if self._enable:
            if not key:
                return True in self._enable.values()
            elif key in self._enable:
                return self._enable[key]
            else:
                return False
        else:
            return False

    def notify_with_all(self, message, error_on_failure=True):
        try:
            # gmail
            self.gmail_notification_factory(message, message)

            # twitter
            self.twitter_notification_factory(message, error_on_failure)

            # telegram
            self.telegram_notification_factory(message)
        except Exception as e:
            self.logger.error(f"Failed to notify all : {e}")

    def gmail_notification_available(self, key=None):
        return self.enabled(key) and \
               GmailService.get_name() in self.notification_type and \
               GmailService.is_setup_correctly(self.config)

    def gmail_notification_factory(self, subject, mail):
        if self.gmail_notification_available():
            gmail_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][CONFIG_SERVICE_INSTANCE]
            result = gmail_service.send_mail(subject, mail)
            if result:
                self.logger.info("Mail sent")
        else:
            self.logger.debug("Mail disabled")

    def telegram_notification_available(self, key=None):
        return self.enabled(key) and \
               TelegramService.get_name() in self.notification_type and \
               TelegramService.is_setup_correctly(self.config)

    def telegram_notification_factory(self, message):
        if self.telegram_notification_available():
            telegram_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE]
            result = telegram_service.send_message(message)
            if result:
                self.logger.info("Telegram message sent")
        else:
            self.logger.debug("Telegram disabled")

    def twitter_notification_available(self, key=None):
        return self.enabled(key) and \
               TwitterService.get_name() in self.notification_type and \
               TwitterService.is_setup_correctly(self.config)

    def twitter_notification_factory(self, tweet, error_on_failure=True):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = twitter_service.post(tweet, error_on_failure)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None

    def twitter_response_factory(self, tweet_instance, tweet, error_on_failure=True):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = twitter_service.respond(tweet_instance.id, tweet, error_on_failure)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None

    def web_interface_notification_available(self, key=None):
        return self.enabled(key) and \
               WebService.get_name() in self.notification_type and \
               WebService.is_available(self.config)

    def web_interface_notification_factory(self, level, title, message):
        if self.web_interface_notification_available():
            add_notification(level, title, message)
        else:
            self.logger.debug("Web interface notification disabled")
        return None

    def send_twitter_notification_if_necessary(self, content, notification_type=None, error_on_failure=True):
        if self.twitter_notification_available(notification_type):
            return self.twitter_notification_factory(content, error_on_failure)
        return None

    def sent_twitter_reply_if_necessary(self, previous_notification, content, notification_type=None,
                                        error_on_failure=True):
        if self.twitter_notification_available(notification_type) \
                and previous_notification is not None \
                and previous_notification.get_tweet_instance() is not None:
            tweet_instance = previous_notification.get_tweet_instance()

            self.twitter_response_factory(tweet_instance, content, error_on_failure)

    def send_web_notification_if_necessary(self, level, title, message, notification_type=None):
        if self.web_interface_notification_available(notification_type):
            self.web_interface_notification_factory(level, title, message)

    def send_telegram_notification_if_necessary(self, content, notification_type=None):
        if self.telegram_notification_available(notification_type):
            self.telegram_notification_factory(content)

    def send_gmail_notification_if_necessary(self, subject, mail, notification_type=None):
        if self.gmail_notification_available(notification_type):
            self.gmail_notification_factory(subject, mail)


class EvaluatorNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.tweet_instance = None

    def notify_state_changed(self, notify_content):
        self.tweet_instance = self.send_twitter_notification_if_necessary(notify_content,
                                                                          CONFIG_NOTIFICATION_PRICE_ALERTS)

        self.send_telegram_notification_if_necessary(notify_content, CONFIG_NOTIFICATION_PRICE_ALERTS)

        self.send_web_notification_if_necessary(InterfaceLevel.INFO, "STATE CHANGED", notify_content,
                                                CONFIG_NOTIFICATION_PRICE_ALERTS)

        return self

    async def notify_alert(self, final_eval, crypto_currency_evaluator, symbol, trader, result, matrix):
        title = f"OCTOBOT ALERT : {crypto_currency_evaluator.crypto_currency} / {result}"

        if self.gmail_notification_available(CONFIG_NOTIFICATION_PRICE_ALERTS):
            profitability, profitability_percent, _, _, _ = await trader.get_trades_manager().get_profitability()

            self.gmail_notification_factory(
                title,
                "OCTOBOT ALERT : {0} / {1} \n {2} \n Current portfolio "
                "profitability : {3} "
                "{4} ({5}%)".format(
                    crypto_currency_evaluator.crypto_currency,
                    result,
                    pprint.pformat(matrix),
                    round(profitability, 2),
                    TradesManager.get_reference_market(self.config),
                    round(profitability_percent, 2)))

        alert_content = PrettyPrinter.cryptocurrency_alert(
            crypto_currency_evaluator.crypto_currency,
            symbol,
            result,
            final_eval)

        self.tweet_instance = self.send_twitter_notification_if_necessary(alert_content,
                                                                          CONFIG_NOTIFICATION_PRICE_ALERTS)

        self.send_telegram_notification_if_necessary(alert_content, CONFIG_NOTIFICATION_PRICE_ALERTS)

        self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, alert_content,
                                                CONFIG_NOTIFICATION_PRICE_ALERTS)

        return self

    def get_tweet_instance(self):
        return self.tweet_instance


class OrdersNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.evaluator_notification = None

    def notify_create(self, evaluator_notification, orders):
        if orders:
            content = orders[0].trader.trader_type_str
            if evaluator_notification is not None:
                self.evaluator_notification = evaluator_notification

            title = "Order(s) creation "
            content += title
            for order in orders:
                content += f"\n- {PrettyPrinter.open_order_pretty_printer(order)}"

            self.sent_twitter_reply_if_necessary(self.evaluator_notification, content, CONFIG_NOTIFICATION_TRADES)

            self.send_telegram_notification_if_necessary(content, CONFIG_NOTIFICATION_TRADES)

            self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, content,
                                                    CONFIG_NOTIFICATION_TRADES)

    def notify_end(self,
                   order_filled,
                   orders_canceled,
                   trade_profitability,
                   portfolio_profitability,
                   portfolio_diff,
                   profitability=False):

        title = "Order status updated"

        content = self._build_notification_content(order_filled, orders_canceled, trade_profitability,
                                                   portfolio_profitability, portfolio_diff, profitability)

        self.sent_twitter_reply_if_necessary(self.evaluator_notification, content, CONFIG_NOTIFICATION_TRADES)

        self.send_telegram_notification_if_necessary(content, CONFIG_NOTIFICATION_TRADES)

        self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, content,
                                                CONFIG_NOTIFICATION_TRADES)

    @staticmethod
    def _build_notification_content(order_filled,
                                    orders_canceled,
                                    trade_profitability,
                                    portfolio_profitability,
                                    portfolio_diff,
                                    profitability=False):
        content = ""
        if order_filled is not None:
            content += f"\n{order_filled.trader.trader_type_str}Order(s) filled : " \
                       f"\n- {PrettyPrinter.open_order_pretty_printer(order_filled)}"

        if orders_canceled is not None and orders_canceled:
            content += f"\n{orders_canceled[0].trader.trader_type_str}Order(s) canceled :"
            for order in orders_canceled:
                content += f"\n- {PrettyPrinter.open_order_pretty_printer(order)}"

        if trade_profitability is not None and profitability:
            content += f"\n\nTrade profitability : {'+' if trade_profitability >= 0 else ''}" \
                       f"{round(trade_profitability * 100, 4)}%"

        if portfolio_profitability is not None and profitability:
            content += f"\nPortfolio profitability : {round(portfolio_profitability, 4)}% " \
                       f"{'+' if portfolio_diff >= 0 else ''}{round(portfolio_diff, 4)}%"

        return content


class InterfaceLevel(Enum):
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
