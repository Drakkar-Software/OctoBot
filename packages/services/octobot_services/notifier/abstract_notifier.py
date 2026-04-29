#  Drakkar-Software OctoBot-Services
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
import abc
import asyncio

import async_channel.util as channel_creator
import async_channel.channels as channels

import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums

import octobot_services.channel as service_channels
import octobot_services.constants as constants
import octobot_services.notification as notifications
import octobot_services.abstract_service_user as abstract_service_user
import octobot_services.util as util


class AbstractNotifier(abstract_service_user.AbstractServiceUser, util.ExchangeWatcher):
    __metaclass__ = abc.ABCMeta
    # Override this key with the identifier of the notifier (used to know if enabled)
    NOTIFICATION_TYPE_KEY = None
    # The service required to run this notifier
    REQUIRED_SERVICES = None
    USE_MAIN_LOOP = False

    def __init__(self, config):
        abstract_service_user.AbstractServiceUser.__init__(self, config)
        util.ExchangeWatcher.__init__(self)
        self.executors = None
        self.logger = self.get_logger()
        self.enabled = self.is_enabled(config)
        self.services = None
        self.previous_notifications_by_identifier = {}
        self.loop = asyncio.get_event_loop()

    async def register_new_exchange_impl(self, exchange_id):
        # if self.is_initialized is False, this notifier has not been initialized and should not be used
        if self.is_initialized and exchange_id not in self.registered_exchanges_ids:
            await self._subscribe_to_order_channel(exchange_id)

    # Override this method to consume a notification when received
    @abc.abstractmethod
    async def _handle_notification(self, notification: notifications.Notification):
        raise NotImplementedError(f"_handle_notification is not implemented")

    async def _send_notification(self, notification: notifications.Notification):
        self.logger.debug(f"Publishing notification: {notification}")
        await self._handle_notification(notification)

    def _send_notification_from_executor(self, notification: notifications.Notification):
        asyncio.run(self._send_notification(notification))

    async def _notification_callback(self, notification: notifications.Notification = None):
        try:
            if self._is_notification_category_enabled(notification):
                if self.USE_MAIN_LOOP:
                    await self._send_notification(notification)
                else:
                    await self.loop.run_in_executor(self.executors, self._send_notification_from_executor, notification)
        except Exception as e:
            self.logger.exception(e, True, f"Exception when handling notification: {e}")

    async def _initialize_impl(self, backtesting_enabled, edited_config) -> bool:
        # make sure to always create the notification channel
        channel = await self._create_notification_channel_if_not_existing()
        if await abstract_service_user.AbstractServiceUser._initialize_impl(self, backtesting_enabled, edited_config):
            self.services = [service.instance() for service in self.REQUIRED_SERVICES]
            await self._subscribe_to_notification_channel(channel)
            return True
        return False

    async def _subscribe_to_notification_channel(self, channel):
        await channel.new_consumer(self._notification_callback)
        self.logger.debug("Registered as notification consumer")

    async def _order_notification_callback(self, exchange, exchange_id, cryptocurrency, symbol, order,
                                           update_type, is_from_bot):
        exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        # Do not notify on existing pre-start orders
        if is_from_bot and not trading_api.get_is_backtesting(exchange_manager):
            order_identifier = f"{exchange}_{order[trading_enums.ExchangeConstantsOrderColumns.ID.value]}"
            # find the last notification for this order if any
            linked_notification = self.previous_notifications_by_identifier[order_identifier] \
                if order_identifier in self.previous_notifications_by_identifier else None
            await self._handle_order_notification(order, linked_notification, order_identifier,
                                                  exchange_manager, exchange)

    async def _handle_order_notification(self, dict_order, linked_notification, order_identifier,
                                         exchange_manager, exchange):
        notification = None
        order_status = trading_api.parse_order_status(dict_order)

        if order_status is trading_enums.OrderStatus.OPEN:
            notification = notifications.OrderCreationNotification(linked_notification, dict_order, exchange)
            # update last notification for this order
            self.previous_notifications_by_identifier[order_identifier] = notification
        else:
            is_simulated = trading_api.is_trader_simulated(exchange_manager)
            if order_status is trading_enums.OrderStatus.EXPIRED or \
                order_status is trading_enums.OrderStatus.CANCELED or \
                    (order_status is trading_enums.OrderStatus.CLOSED
                     and dict_order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] == 0):
                notification = notifications.OrderEndNotification(
                    linked_notification, None, exchange, [dict_order], None, None, None, False, is_simulated
                )
            elif order_status in (trading_enums.OrderStatus.CLOSED, trading_enums.OrderStatus.FILLED):
                trade_pnl = trading_api.get_trade_pnl(
                    exchange_manager, order_id=dict_order[trading_enums.ExchangeConstantsOrderColumns.ID.value]
                )
                pnl_percent = None
                if trade_pnl:
                    _, pnl_percent = trade_pnl.get_profits()
                notification = notifications.OrderEndNotification(
                    linked_notification, dict_order, exchange, [], pnl_percent, None, None, True, is_simulated
                )
            # remove order from previous_notifications_by_identifier: no more notification from it to be received
            if order_identifier in self.previous_notifications_by_identifier:
                self.previous_notifications_by_identifier.pop(order_identifier)
        await self._notification_callback(notification)

    async def _subscribe_to_order_channel(self, exchange_id):
        try:
            await trading_api.subscribe_to_order_channel(self._order_notification_callback, exchange_id)
        except KeyError:
            self.logger.error("No order channel to subscribe to: impossible to send order notifications")

    @classmethod
    def is_enabled(cls, config):
        if cls.NOTIFICATION_TYPE_KEY is None:
            cls.get_logger().warning(f"{cls.get_name()}.NOTIFICATION_TYPE_KEY is not set, it has to be set to identify "
                                     f"and activate this notifier.")
        return cls.NOTIFICATION_TYPE_KEY in AbstractNotifier._get_activated_notification_keys(config)

    @staticmethod
    def _get_activated_notification_keys(config):
        if constants.CONFIG_CATEGORY_NOTIFICATION in config \
                and constants.CONFIG_NOTIFICATION_TYPE in config[constants.CONFIG_CATEGORY_NOTIFICATION]:
            return config[constants.CONFIG_CATEGORY_NOTIFICATION][constants.CONFIG_NOTIFICATION_TYPE]
        return []

    @staticmethod
    async def _create_notification_channel_if_not_existing() -> channels.Channel:
        try:
            return channels.get_chan(service_channels.NotificationChannel.get_name())
        except KeyError:
            channel = await channel_creator.create_channel_instance(service_channels.NotificationChannel,
                                                                    channels.set_chan)
            await channel.register_producer(service_channels.NotificationChannelProducer.instance(channel))
            return channel

    def _is_notification_category_enabled(self, notification):
        return constants.CONFIG_CATEGORY_NOTIFICATION in self.config and \
               self.config[constants.CONFIG_CATEGORY_NOTIFICATION].get(notification.category.value, True)
