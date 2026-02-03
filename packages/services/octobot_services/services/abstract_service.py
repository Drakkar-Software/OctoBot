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
import typing

import octobot_commons.configuration as configuration
import octobot_commons.singleton as singleton
import octobot_commons.logging as logging

import octobot_services.constants as constants
import octobot_services.services.read_only_info as read_only_info


class AbstractService(singleton.Singleton):
    __metaclass__ = abc.ABCMeta

    BACKTESTING_ENABLED = False

    def __init__(self):
        super().__init__()
        self.logger: typing.Optional[logging.BotLogger] = None
        self.config: typing.Optional[dict] = None
        self.edited_config: typing.Optional[dict] = None
        self.creation_error_message: typing.Optional[str] = None
        self._created: bool = True
        self._healthy: bool = False
        self._has_been_created: bool = False

    def set_has_been_created(self, value):
        self._has_been_created = value

    def get_has_been_created(self):
        return self._has_been_created

    def is_healthy(self):
        return self._healthy

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_fields_description(self) -> dict:
        """
        :return: the service configuration keys with their description
        """
        return {}

    def get_default_value(self) -> dict:
        """
        :return: the service configuration keys with their default value
        """
        return {}

    def get_required_config(self) -> list:
        """
        :return: the list of required (not optional) configuration keys
        """
        return []

    def get_read_only_info(self) -> list[read_only_info.ReadOnlyInfo]:
        return []

    def is_improved_by_extensions(self) -> bool:
        return False

    @classmethod
    def get_help_page(cls) -> str:
        """
        :return: the url of the help page with this service
        """
        return ""

    # Override this method if a user is to be registered in this service (ie: TelegramService)
    def register_user(self, user_key):
        pass

    # Override this method if a service feed is located in this service (ie: TelegramService)
    async def start_service_feed(self):
        pass

    # Override this method to know if an updater is already running
    def is_running(self):
        return False

    # Returns true if all the service has an instance in config
    @staticmethod
    @abc.abstractmethod
    def is_setup_correctly(config):
        raise NotImplementedError("is_setup_correctly not implemented")

    # Override this method to perform additional checks
    @staticmethod
    def get_is_enabled(config):
        return True

    # implement locally if the service has thread(s) to stop
    async def stop(self):
        pass

    # implement locally if the service shouldn't raise warning at startup if configuration is not set
    @staticmethod
    def get_should_warn():
        return True

    # Returns true if all the configuration is available
    @abc.abstractmethod
    def has_required_configuration(self):
        raise NotImplementedError("has_required_configuration not implemented")

    # Returns the service's endpoint
    @abc.abstractmethod
    def get_endpoint(self) -> None:
        raise NotImplementedError("get_endpoint not implemented")

    # Called to put in the right service in config
    @abc.abstractmethod
    def get_type(self) -> None:
        raise NotImplementedError("get_type not implemented")

    # Called after service setup
    @abc.abstractmethod
    async def prepare(self) -> None:
        raise NotImplementedError("prepare not implemented")

    # Called by say_hello after service is prepared, return relevant service information and a boolean for
    # success or failure
    @abc.abstractmethod
    def get_successful_startup_message(self):
        raise NotImplementedError("get_successful_startup_message not implemented")

    def get_website_url(self) -> str:
        # Override with the real url
        return ""

    def get_brand_name(self):
        return self.get_type()

    def get_logo(self):
        # Default services logos are fount using https://github.com/edent/SuperTinyIcons
        # Override to customize this behavior
        return f"https://raw.githubusercontent.com/edent/SuperTinyIcons/master/images/svg/{self.get_brand_name()}.svg"

    def check_required_config(self, config):
        return all(key in config for key in self.get_required_config()) and \
            not configuration.has_invalid_default_config_value(*(config[key] for key in self.get_required_config()))

    def log_connection_error_message(self, e):
        self.logger.error(f"{self.get_name()} is failing to connect, please check your internet connection: {e}")

    async def say_hello(self):
        message, self._healthy = self.get_successful_startup_message()
        if self._healthy and message:
            self.logger.info(message)
        return self._healthy

    def save_service_config(self, service_key, service_config, update=False):
        """
        Save the service's config into the user config file
        :param service_key: the key of the service config in file
        :param service_config: the updated config
        :param update: when true, the service configuration dict will be updated using the new data, it will
        be replaced otherwise
        :return: None
        """
        if update and service_key in self.edited_config.config[constants.CONFIG_CATEGORY_SERVICES]:
            self.edited_config.config[constants.CONFIG_CATEGORY_SERVICES][service_key].update(service_config)
        else:
            self.edited_config.config[constants.CONFIG_CATEGORY_SERVICES][service_key] = service_config
        self.edited_config.save()
