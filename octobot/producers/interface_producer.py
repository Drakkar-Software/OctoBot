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
from octobot.channels.octobot_channel import OctoBotChannelProducer
from octobot.constants import PROJECT_NAME, LONG_VERSION, CONFIG_KEY
from octobot_backtesting.api.backtesting import is_backtesting_enabled
from octobot_commons.enums import OctoBotChannelSubjects
from octobot_services.api.interfaces import create_interface_factory, initialize_global_project_data, is_enabled, \
    start_interfaces, is_enabled_in_backtesting
from octobot_services.api.notification import create_notifier_factory, is_enabled_in_config, \
    process_pending_notifications
from octobot_services.interfaces.util.bot import get_bot_api
from octobot_services.managers.interface_manager import stop_interfaces
from octobot_services.consumers.octobot_channel_consumer import OctoBotChannelServiceActions as ServiceActions, \
    OctoBotChannelServiceDataKeys as ServiceKeys


class InterfaceProducer(OctoBotChannelProducer):
    """Initializer class:
    - Initialize services, constants and tools
    """

    def __init__(self, channel, octobot):
        super().__init__(channel)
        self.octobot = octobot

        self.interfaces = []
        self.notifiers = []
        self.to_create_notifiers_count = 0

    async def start(self):
        in_backtesting = is_backtesting_enabled(self.octobot.config)
        await self._create_interfaces(in_backtesting)
        await self._create_notifiers(in_backtesting)
        await self.start_interfaces()

    async def start_interfaces(self):
        to_start_interfaces = self.interfaces
        started_interfaces = await start_interfaces(to_start_interfaces)
        if len(started_interfaces) != len(to_start_interfaces):
            missing_interfaces = [interface.get_name()
                                  for interface in to_start_interfaces
                                  if interface not in started_interfaces]
            self.logger.error(
                f"{', '.join(missing_interfaces)} interface{'s' if len(missing_interfaces) > 1 else ''} "
                f"did not start properly.")

    async def register_exchange(self, exchange_id):
        for to_notify_instance in self.interfaces + self.notifiers:
            await self._register_exchange(to_notify_instance, exchange_id)

    async def register_interface(self, instance):
        self.interfaces.append(instance)
        await self._register_existing_exchanges(instance)

    async def register_notifier(self, instance):
        self.notifiers.append(instance)
        await self._register_existing_exchanges(instance)
        if len(self.notifiers) == self.to_create_notifiers_count:
            await process_pending_notifications()

    async def _register_existing_exchanges(self, instance):
        for exchange_id in self.octobot.exchange_producer.exchange_manager_ids:
            await self._register_exchange(instance, exchange_id)

    async def _create_interfaces(self, in_backtesting):
        # do not overwrite data in case of inner bots init (backtesting)
        if get_bot_api() is None:
            initialize_global_project_data(self.octobot.octobot_api, PROJECT_NAME, LONG_VERSION)
        interface_factory = create_interface_factory(self.octobot.config)
        interface_list = interface_factory.get_available_interfaces()
        for interface_class in interface_list:
            await self._create_interface_if_relevant(interface_factory, interface_class, in_backtesting,
                                                     self.octobot.get_edited_config(CONFIG_KEY))

    async def _create_notifiers(self, in_backtesting):
        notifier_factory = create_notifier_factory(self.octobot.config)
        notifier_list = notifier_factory.get_available_notifiers()
        for notifier_class in notifier_list:
            await self._create_notifier_class_if_relevant(notifier_factory, notifier_class, in_backtesting,
                                                          self.octobot.get_edited_config(CONFIG_KEY))

    async def _create_interface_if_relevant(self, interface_factory, interface_class,
                                            backtesting_enabled, edited_config):
        if self._is_interface_relevant(interface_class, backtesting_enabled):
            await self.send(bot_id=self.octobot.bot_id,
                            subject=OctoBotChannelSubjects.CREATION.value,
                            action=ServiceActions.INTERFACE.value,
                            data={
                                ServiceKeys.EDITED_CONFIG.value: edited_config,
                                ServiceKeys.BACKTESTING_ENABLED.value: backtesting_enabled,
                                ServiceKeys.CLASS.value: interface_class,
                                ServiceKeys.FACTORY.value: interface_factory
                            })

    async def _create_notifier_class_if_relevant(self, notifier_factory, notifier_class,
                                                 backtesting_enabled, edited_config):
        if self._is_notifier_relevant(notifier_class, backtesting_enabled):
            await self.send(bot_id=self.octobot.bot_id,
                            subject=OctoBotChannelSubjects.CREATION.value,
                            action=ServiceActions.NOTIFICATION.value,
                            data={
                                ServiceKeys.EDITED_CONFIG.value: edited_config,
                                ServiceKeys.BACKTESTING_ENABLED.value: backtesting_enabled,
                                ServiceKeys.CLASS.value: notifier_class,
                                ServiceKeys.FACTORY.value: notifier_factory
                            })
            self.to_create_notifiers_count += 1

    async def _register_exchange(self, to_notify_instance, exchange_id):
        await self.send(bot_id=self.octobot.bot_id,
                        subject=OctoBotChannelSubjects.UPDATE.value,
                        action=ServiceActions.EXCHANGE_REGISTRATION.value,
                        data={
                            ServiceKeys.INSTANCE.value: to_notify_instance,
                            ServiceKeys.EXCHANGE_ID.value: exchange_id,
                        })

    def _is_interface_relevant(self, interface_class, backtesting_enabled):
        return is_enabled(interface_class) and \
               all(service.get_is_enabled(self.octobot.config) for service in interface_class.REQUIRED_SERVICES) and \
               (not backtesting_enabled or (backtesting_enabled and is_enabled_in_backtesting(interface_class)))

    def _is_notifier_relevant(self, notifier_class, backtesting_enabled):
        return is_enabled_in_config(notifier_class, self.octobot.config) and \
               all(service.get_is_enabled(self.octobot.config)
                   for service in notifier_class.REQUIRED_SERVICES) and \
               not backtesting_enabled

    async def stop(self):
        await stop_interfaces(self.interfaces)
