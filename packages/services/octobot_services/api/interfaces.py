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
import asyncio

import octobot_commons.channels_name as channels_names
import async_channel.channels as channels
import octobot_services.interfaces as interfaces
import octobot_services.managers as managers
import octobot_services.api.service_feeds as service_feeds_api


def initialize_global_project_data(bot_id: str, project_name: str, project_version: str) -> None:
    interfaces.AbstractInterface.initialize_global_project_data(bot_id, project_name, project_version)


def create_interface_factory(config: dict) -> interfaces.InterfaceFactory:
    return interfaces.InterfaceFactory(config)


def is_enabled(interface_class: interfaces.AbstractInterface) -> bool:
    return interface_class.enabled


async def send_user_command(bot_id, subject, action, data, wait_for_processing=False) -> bool:
    try:
        channel = channels.get_chan(channels_names.OctoBotUserChannelsName.USER_COMMANDS_CHANNEL.value)
        await channel.get_internal_producer().send(
            bot_id=bot_id,
            subject=subject,
            action=action,
            data=data
        )
        if wait_for_processing:
            producers = channel.producers
            if channel.internal_producer is not None:
                producers.append(channel.internal_producer)
            await asyncio.gather(*(producer.wait_for_processing() for producer in producers))
        return True
    except KeyError:
        return False


def is_enabled_in_backtesting(interface_class) -> bool:
    if not interface_class.REQUIRED_SERVICES:
        return True
    return all(
        service_feeds_api.is_service_used_by_backtestable_feed(service)
        for service in interface_class.REQUIRED_SERVICES
    )


def is_interface_relevant(config, interface_class, backtesting_enabled):
    return is_enabled(interface_class) and \
           all(service.get_is_enabled(config) for service in interface_class.REQUIRED_SERVICES) and \
           (not backtesting_enabled or (backtesting_enabled and is_enabled_in_backtesting(interface_class)))


def disable_interfaces(interface_identifier: str) -> int:
    disabled_interfaces = 0
    normalized_identifier = interface_identifier.lower()
    for interface_class in interfaces.InterfaceFactory.get_available_interfaces():
        if normalized_identifier in interface_class.__name__.lower():
            interface_class.enabled = False
            disabled_interfaces += 1
    return disabled_interfaces


# Return the list of started interfaces
async def start_interfaces(interfaces: list) -> list:
    return await managers.start_interfaces(interfaces)


async def stop_interfaces(interfaces: list) -> None:
    await managers.stop_interfaces(interfaces)
