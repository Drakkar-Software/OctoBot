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
import octobot_services.services as services


async def stop_services():
    for service_instance in _get_service_instances():
        try:
            logging.get_logger(__name__).debug(f"Stopping {service_instance.get_name()} ...")
            await service_instance.stop()
            logging.get_logger(__name__).debug(f"Stopped {service_instance.get_name()}")
        except Exception as e:
            raise e


def _get_service_instances():
    return [service_class.instance() for service_class in services.ServiceFactory.get_available_services()]
