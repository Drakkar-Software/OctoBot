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

from config import CONFIG_CATEGORY_SERVICES, CONFIG_SERVICE_INSTANCE
from services.abstract_service import AbstractService
from tools.logging.logging_util import get_logger


class ServiceCreator:

    @classmethod
    def get_name(cls):
        return cls.__name__

    @staticmethod
    async def create_services(config, backtesting_enabled):
        logger = get_logger(ServiceCreator.get_name())
        await ServiceCreator.create_services_from_abstract(logger, config, backtesting_enabled)

    @staticmethod
    async def create_services_from_abstract(logger, config, backtesting_enabled):
        for service_class in AbstractService.__subclasses__():
            await ServiceCreator.create_service(logger, service_class, config, backtesting_enabled)

    @staticmethod
    async def create_service(logger, service_class, config, backtesting_enabled):
        service_instance = service_class()
        if service_instance.get_is_enabled(config) and \
                (not backtesting_enabled or service_instance.BACKTESTING_ENABLED):
            service_instance.set_logger(get_logger(service_class.get_name()))
            service_instance.set_config(config)
            if service_instance.has_required_configuration():
                try:
                    await service_instance.prepare()

                    config[CONFIG_CATEGORY_SERVICES][service_instance.get_type()][CONFIG_SERVICE_INSTANCE] = \
                        service_instance

                    if not await service_instance.say_hello():
                        logger.warning(f"{service_class.get_name()} initial checkup failed.")
                except Exception as e:
                    logger.error(f"{service_class.get_name()} preparation produced the following error: {e}")
                    logger.exception(e)
            else:
                if service_instance.get_should_warn():
                    logger.warning(f"{service_class.get_name()} can't be initialized: configuration is missing, "
                                   f"wrong or incomplete !")

    @staticmethod
    def get_service_instances(config):
        instances = []
        for services in config[CONFIG_CATEGORY_SERVICES]:
            if CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][services]:
                instance = config[CONFIG_CATEGORY_SERVICES][services][CONFIG_SERVICE_INSTANCE]
                if isinstance(instance, list):
                    for i in instance:
                        instances.append(i)
                else:
                    instances.append(instance)
        return instances
