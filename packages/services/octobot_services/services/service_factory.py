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

import typing

import octobot_commons.logging as logging

import octobot.configuration_manager as configuration_manager
import octobot.enums as octobot_enums
import octobot_services.constants as constants
import octobot_services.services as services


class ServiceFactory:
    def __init__(self, config):
        self.logger = logging.get_logger(self.__class__.__name__)
        self.config = config

    @staticmethod
    def get_available_services() -> list:
        return [service_class for service_class in services.AbstractService.__subclasses__() if service_class is not services.AbstractAIService and service_class is not services.AbstractWebSearchService]

    @staticmethod
    def get_available_ai_services() -> list:
        return [service_class for service_class in services.AbstractAIService.__subclasses__()]

    @staticmethod
    def get_available_web_search_services() -> list:
        return [service_class for service_class in services.AbstractWebSearchService.__subclasses__()]

    async def create_or_get_service(self, service_class, backtesting_enabled, edited_config) -> typing.Tuple[bool, str]:
        """
        create_or_get_service will create a service instance if it doesn't exist, check the existing one otherwise
        :param service_class: the class of the service to create
        :return: True if the created service is working properly, False otherwise
        """
        service_instance = service_class.instance()
        if service_instance.get_has_been_created():
            return service_instance.is_healthy(), service_instance.creation_error_message
        else:
            return (
                await self._create_service(service_instance, backtesting_enabled, edited_config),
                service_instance.creation_error_message
            )

    async def _create_service(self, service, backtesting_enabled, edited_config) -> bool:
        service.set_has_been_created(True)
        service.logger = logging.get_logger(service.get_name())
        service.config = self.config
        service.edited_config = edited_config
        if service.has_required_configuration():
            return await self._perform_checkup(service)
        else:
            if service.get_should_warn():
                service.creation_error_message = (
                    f"Invalid configuration, visit {service.get_help_page()} for more details."
                )
                self.logger.info(f"{service.get_name()} can't be initialized: {service.creation_error_message}")
        return False

    async def _perform_checkup(self, service) -> bool:
        try:
            await service.prepare()
            if self.config:
                if constants.CONFIG_CATEGORY_SERVICES not in self.config:
                    self.config[constants.CONFIG_CATEGORY_SERVICES] = {}
                if service.get_type() not in self.config[constants.CONFIG_CATEGORY_SERVICES]:
                    self.config[constants.CONFIG_CATEGORY_SERVICES][service.get_type()] = {}
                self.config[constants.CONFIG_CATEGORY_SERVICES][service.get_type()][
                    constants.CONFIG_SERVICE_INSTANCE] = service
            if await service.say_hello():
                return service.is_healthy()
            else:
                self.logger.warning(f"{service.get_name()} initial checkup failed.")
        except Exception as e:
            self.logger.exception(e, True, f"{service.get_name()} preparation produced the following error: {e}")
            if (
                configuration_manager.get_distribution(self.config) is octobot_enums.OctoBotDistribution.NODE
                and service.get_type() == constants.CONFIG_NODE_API
            ):
                import octobot_node.scheduler as scheduler_module
                import octobot.community.node_journal.enums as journal_enums
                import octobot.community.node_journal.recording_context as journal_recording_context
                import octobot.community.node_journal.lifecycle as journal_startup
                journal_recording_context.node_api_startup_failure(
                    error=e,
                    startup_phase=journal_enums.JournalStartupPhase.NODE_API_START,
                    force_exit=False,
                    config=self.config,
                    scheduler_init_failure_was_recorded=scheduler_module.scheduler_init_failure_was_recorded,
                    record_node_startup_failed=journal_startup.record_node_startup_failed,
                )
        return False

    @staticmethod
    def has_already_been_created(service_class):
        return service_class.instance().get_has_been_created()
