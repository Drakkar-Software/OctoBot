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
import octobot_commons.logging as logging


def _interface_uses_background_thread(interface) -> bool:
    return interface.__class__.__name__ == "NodeApiInterface"


async def start_interfaces(interfaces: list):
    logger = logging.get_logger(__name__)
    started_interfaces = []
    for interface in interfaces:
        interface_name = interface.get_name()
        background_thread = _interface_uses_background_thread(interface)
        if background_thread:
            logger.info("Starting %s (threaded=True)", interface_name)
        started = await interface.start()
        if background_thread:
            logger.info("Started %s (spawned=%s)", interface_name, started)
        if started:
            started_interfaces.append(interface)
    return started_interfaces


async def start_interface(interface):
    return await interface.start()


async def stop_interfaces(interfaces: list):
    for interface in interfaces:
        logging.get_logger(__name__).debug(f"Stopping {interface.get_name()} ...")
        await interface.stop()
        logging.get_logger(__name__).debug(f"Stopped {interface.get_name()}")
