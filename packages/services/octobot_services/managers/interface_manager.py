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


async def start_interfaces(interfaces: list):
    started_interfaces = []
    for interface in interfaces:
        if await interface.start():
            started_interfaces.append(interface)
    return started_interfaces


async def start_interface(interface):
    return await interface.start()


async def stop_interfaces(interfaces: list):
    for interface in interfaces:
        logging.get_logger(__name__).debug(f"Stopping {interface.get_name()} ...")
        await interface.stop()
        logging.get_logger(__name__).debug(f"Stopped {interface.get_name()}")
