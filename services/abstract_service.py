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

from abc import ABCMeta, abstractmethod

from backtesting import backtesting_enabled
from tools.config_manager import ConfigManager


class AbstractService:
    __metaclass__ = ABCMeta

    BACKTESTING_ENABLED = False

    def __init__(self):
        super().__init__()
        self.logger = None
        self.config = None
        self.enabled = True

    @classmethod
    def get_name(cls):
        return cls.__name__

    def get_fields_description(self):
        return {}

    def get_default_value(self):
        return {}

    def get_required_config(self):
        return {}

    # Override this method if a user is to be registered in this service (ie: TelegramService)
    def register_user(self, user_key):
        pass

    # Override this method if a dispatcher is located in this service (ie: TelegramService)
    def start_dispatcher(self):
        pass

    @classmethod
    def get_help_page(cls) -> str:
        return ""

    # Returns true if all the service has an instance in config
    @staticmethod
    @abstractmethod
    def is_setup_correctly(config):
        raise NotImplementedError("is_setup_correctly not implemented")

    @classmethod
    def should_be_ready(cls, config):
        on_backtesting = backtesting_enabled(config)
        return not on_backtesting or (on_backtesting and cls.BACKTESTING_ENABLED)

    # Used to provide a new logger for this particular indicator
    def set_logger(self, logger):
        self.logger = logger

    # Used to provide the global config
    def set_config(self, config):
        self.config = config

    # If this service is enabled
    def get_is_enabled(self, config):
        return self.enabled

    # implement locally if the service has thread(s) to stop
    def stop(self):
        pass

    # implement locally if the service shouldn't raise warning at startup if configuration is not set
    @staticmethod
    def get_should_warn():
        return True

    # Returns true if all the configuration is available
    @abstractmethod
    def has_required_configuration(self):
        raise NotImplementedError("has_required_configuration not implemented")

    # Returns the service's endpoint
    @abstractmethod
    def get_endpoint(self) -> None:
        raise NotImplementedError("get_endpoint not implemented")

    # Called to put in the right service in config
    @abstractmethod
    def get_type(self) -> None:
        raise NotImplementedError("get_type not implemented")

    # Called after service setup
    @abstractmethod
    async def prepare(self) -> None:
        raise NotImplementedError("prepare not implemented")

    # Called by say_hello after service is prepared, return relevant service information and a boolean for
    # success or failure
    @abstractmethod
    def get_successful_startup_message(self):
        raise NotImplementedError("get_successful_startup_message not implemented")

    def check_required_config(self, config):
        return all(key in config for key in self.get_required_config()) and \
            not ConfigManager.has_invalid_default_config_value(*(config[key] for key in self.get_required_config()))

    def log_connection_error_message(self, e):
        self.logger.error(f"{self.get_name()} is failing to connect, please check your internet connection: {e}")

    async def say_hello(self):
        message, success = self.get_successful_startup_message()
        if success:
            self.logger.info(message)
        return success
