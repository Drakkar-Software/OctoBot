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

from abc import ABCMeta
from enum import Enum

from config import CONFIG_CATEGORY_NOTIFICATION, CONFIG_CATEGORY_SERVICES, \
    CONFIG_SERVICE_INSTANCE, CONFIG_TWITTER, CONFIG_TELEGRAM, CONFIG_NOTIFICATION_PRICE_ALERTS, \
    CONFIG_NOTIFICATION_TRADES, CONFIG_NOTIFICATION_TYPE, CONFIG_WEB
from interfaces.web import add_notification
from services import TwitterService, TelegramService, WebService
from tools.logging.logging_util import get_logger
from tools.pretty_printer import PrettyPrinter


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

    async def notify_with_all(self, message, error_on_failure=True, italic_markdown=True):
        try:
            message_markdown = message
            if italic_markdown:
                message_markdown = f"_{message_markdown}_"

            # twitter
            await self.twitter_notification_factory(message, error_on_failure)

            # telegram
            await self.telegram_notification_factory(message_markdown, markdown=True)
        except Exception as e:
            self.logger.error(f"Failed to notify all : {e}")

    def telegram_notification_available(self, key=None):
        return self.enabled(key) and \
               self._service_instance_is_present(CONFIG_TELEGRAM) and \
               self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE].get_type() \
               in self.notification_type and \
               TelegramService.is_setup_correctly(self.config)

    async def telegram_notification_factory(self, message, markdown=False):
        if self.telegram_notification_available():
            telegram_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TELEGRAM][CONFIG_SERVICE_INSTANCE]
            result = await telegram_service.send_message(message, markdown=markdown)
            if result:
                self.logger.info("Telegram message sent")
        else:
            self.logger.debug("Telegram disabled")

    def twitter_notification_available(self, key=None):
        return self.enabled(key) and \
               self._service_instance_is_present(CONFIG_TWITTER) and \
               self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE].get_type() \
               in self.notification_type and \
               TwitterService.is_setup_correctly(self.config)

    async def twitter_notification_factory(self, tweet, error_on_failure=True):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = await twitter_service.post(tweet, error_on_failure)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None

    async def twitter_response_factory(self, tweet_instance, tweet, error_on_failure=True):
        if self.twitter_notification_available():
            twitter_service = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_TWITTER][CONFIG_SERVICE_INSTANCE]
            result = await twitter_service.respond(tweet_instance.id, tweet, error_on_failure)
            if result is not None:
                self.logger.info("Twitter sent")
            return result
        else:
            self.logger.debug("Twitter notification disabled")
        return None

    def web_interface_notification_available(self, key=None):
        return self.enabled(key) and \
               CONFIG_WEB in self.notification_type and \
               WebService.is_available(self.config)

    async def web_interface_notification_factory(self, level, title, message):
        if self.web_interface_notification_available():
            await add_notification(level, title, message)
        else:
            self.logger.debug("Web interface notification disabled")
        return None

    async def send_twitter_notification_if_necessary(self, content, notification_type=None, error_on_failure=True):
        if self.twitter_notification_available(notification_type):
            return await self.twitter_notification_factory(content, error_on_failure)
        return None

    async def sent_twitter_reply_if_necessary(self, previous_notification, content,
                                              notification_type=None,
                                              error_on_failure=True):
        if self.twitter_notification_available(notification_type) \
                and previous_notification is not None \
                and previous_notification.get_tweet_instance() is not None:
            tweet_instance = previous_notification.get_tweet_instance()

            await self.twitter_response_factory(tweet_instance, content, error_on_failure)

    async def send_web_notification_if_necessary(self, level, title, message, notification_type=None):
        if self.web_interface_notification_available(notification_type):
            await self.web_interface_notification_factory(level, title, message)

    async def send_telegram_notification_if_necessary(self, content, notification_type=None, markdown=False):
        if self.telegram_notification_available(notification_type):
            await self.telegram_notification_factory(content, markdown=markdown)

    def _service_instance_is_present(self, service_type):
        return service_type in self.config[CONFIG_CATEGORY_SERVICES] and \
               CONFIG_SERVICE_INSTANCE in self.config[CONFIG_CATEGORY_SERVICES][service_type]


class EvaluatorNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.tweet_instance = None

    async def notify_state_changed(self, notify_content):
        self.tweet_instance = await self.send_twitter_notification_if_necessary(notify_content,
                                                                                CONFIG_NOTIFICATION_PRICE_ALERTS)

        await self.send_telegram_notification_if_necessary(notify_content, CONFIG_NOTIFICATION_PRICE_ALERTS,
                                                           markdown=True)

        await self.send_web_notification_if_necessary(InterfaceLevel.INFO, "STATE CHANGED", notify_content,
                                                      CONFIG_NOTIFICATION_PRICE_ALERTS)

        return self

    async def notify_alert(self, final_eval, crypto_currency_evaluator, symbol, trader, result, matrix):
        title = f"OCTOBOT ALERT : {crypto_currency_evaluator.crypto_currency} / {result}"

        alert_content, alert_content_markdown = PrettyPrinter.cryptocurrency_alert(
            crypto_currency_evaluator.crypto_currency,
            symbol,
            result,
            final_eval)

        self.tweet_instance = await self.send_twitter_notification_if_necessary(alert_content,
                                                                                CONFIG_NOTIFICATION_PRICE_ALERTS)

        await self.send_telegram_notification_if_necessary(alert_content_markdown, CONFIG_NOTIFICATION_PRICE_ALERTS,
                                                           markdown=True)

        await self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, alert_content,
                                                      CONFIG_NOTIFICATION_PRICE_ALERTS)

        return self

    def get_tweet_instance(self):
        return self.tweet_instance


class OrdersNotification(Notification):
    def __init__(self, config):
        super().__init__(config)
        self.evaluator_notification = None

    async def notify_create(self, evaluator_notification, orders):
        if orders:
            content = orders[0].trader.trader_type_str
            content_markdown = f"*{orders[0].trader.trader_type_str}*"
            if evaluator_notification is not None:
                self.evaluator_notification = evaluator_notification

            title = "Order(s) creation "
            content += title
            content_markdown += title
            for order in orders:
                content += f"\n- {PrettyPrinter.open_order_pretty_printer(order)}"
                content_markdown += f"\n- {PrettyPrinter.open_order_pretty_printer(order, markdown=True)}"

            await self.sent_twitter_reply_if_necessary(self.evaluator_notification, content, CONFIG_NOTIFICATION_TRADES)

            await self.send_telegram_notification_if_necessary(content_markdown, CONFIG_NOTIFICATION_TRADES,
                                                               markdown=True)

            await self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, content,
                                                          CONFIG_NOTIFICATION_TRADES)

    async def notify_end(self,
                         order_filled,
                         orders_canceled,
                         trade_profitability,
                         portfolio_profitability,
                         portfolio_diff,
                         profitability=False):

        title = "Order status updated"

        content, content_markdown = self._build_notification_content(order_filled, orders_canceled, trade_profitability,
                                                                     portfolio_profitability, portfolio_diff,
                                                                     profitability)

        await self.sent_twitter_reply_if_necessary(self.evaluator_notification, content, CONFIG_NOTIFICATION_TRADES)

        await self.send_telegram_notification_if_necessary(content_markdown, CONFIG_NOTIFICATION_TRADES, markdown=True)

        await self.send_web_notification_if_necessary(InterfaceLevel.INFO, title, content, CONFIG_NOTIFICATION_TRADES)

    @staticmethod
    def _build_notification_content(order_filled,
                                    orders_canceled,
                                    trade_profitability,
                                    portfolio_profitability,
                                    portfolio_diff,
                                    profitability=False):
        content = ""
        content_markdown = ""
        if order_filled is not None:
            content += f"\n{order_filled.trader.trader_type_str}Order(s) filled : " \
                f"\n- {PrettyPrinter.open_order_pretty_printer(order_filled)}"
            content_markdown += f"\n*{order_filled.trader.trader_type_str}*Order(s) filled : " \
                f"\n- {PrettyPrinter.open_order_pretty_printer(order_filled, markdown=True)}"

        if orders_canceled is not None and orders_canceled:
            content += f"\n{orders_canceled[0].trader.trader_type_str}Order(s) canceled :"
            content_markdown += f"\n*{orders_canceled[0].trader.trader_type_str}*Order(s) canceled :"
            for order in orders_canceled:
                content += f"\n- {PrettyPrinter.open_order_pretty_printer(order)}"
                content_markdown += f"\n- {PrettyPrinter.open_order_pretty_printer(order, markdown=True)}"

        if trade_profitability is not None and profitability:
            content += f"\n\nTrade profitability : {'+' if trade_profitability >= 0 else ''}" \
                f"{round(trade_profitability * 100, 4)}%"
            content_markdown += f"\nTrade profitability : *{'+' if trade_profitability >= 0 else ''}" \
                f"{round(trade_profitability * 100, 4)}%*"

        if portfolio_profitability is not None and profitability:
            content += f"\nPortfolio profitability : {round(portfolio_profitability, 4)}% " \
                f"{'+' if portfolio_diff >= 0 else ''}{round(portfolio_diff, 4)}%"
            content_markdown += f"\nPortfolio profitability : `{round(portfolio_profitability, 4)}% " \
                f"{'+' if portfolio_diff >= 0 else ''}{round(portfolio_diff, 4)}%`"

        return content, content_markdown


class InterfaceLevel(Enum):
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
