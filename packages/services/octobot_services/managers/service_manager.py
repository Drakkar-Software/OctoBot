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

import octobot_commons.logging as logging
import octobot_services.constants as constants
import octobot_services.services as services

async def stop_services():
    logger = logging.get_logger(__name__)
    for service_instance in _get_service_instances():
        service_name = service_instance.get_name()
        try:
            logger.debug(f"Stopping {service_name} ...")
            await asyncio.wait_for(
                service_instance.stop(),
                timeout=constants.SERVICE_STOP_TIMEOUT_SECONDS,
            )
            logger.debug(f"Stopped {service_name}")
        except asyncio.TimeoutError:
            logger.warning(
                f"Timed out stopping {service_name} after {constants.SERVICE_STOP_TIMEOUT_SECONDS}s, continuing shutdown"
            )
        except Exception as error:
            logger.exception(
                error,
                True,
                f"Error when stopping {service_name}: {error}",
            )


def _get_service_instances():
    return [service_class.instance() for service_class in services.ServiceFactory.get_available_services()]
