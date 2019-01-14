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

import logging

logging.getLogger("notifiers").setLevel(logging.WARNING)

import notifiers
from notifiers import NoSuchNotifierError

from config import CONFIG_NOTIFIER, CONFIG_CATEGORY_SERVICES
from services.abstract_service import AbstractService


class NotifierService(AbstractService):
    PUSHOVER = None
    SERVICE_CONFIG = None

    def __init__(self):
        super().__init__()
        self.pushover = self.__class__.PUSHOVER
        self.name = self.pushover.name
        self.service_config = self.__class__.SERVICE_CONFIG

    @classmethod
    def get_fields_description(cls):
        return {key: key
                for key in cls.get_required_config()}

    @classmethod
    def get_default_value(cls):
        return {key: ""
                for key in cls.get_required_config()}

    @classmethod
    def get_required_config(cls):
        required_list = cls.PUSHOVER.required["required"]
        required_list.remove('message')
        return required_list

    @classmethod
    def get_help_page(cls) -> str:
        return "https://github.com/Drakkar-Software/OctoBot/wiki/Notifier-interface#notifier-interface"

    @classmethod
    def is_available(cls, interface):
        try:
            return notifiers.get_notifier(interface)
        except NoSuchNotifierError:
            return False

    @staticmethod
    def is_setup_correctly(config):
        return True

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and self.get_provider_name() in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][self.get_provider_name()])

    def get_endpoint(self):
        return self.get_provider_name()

    def get_provider_name(self):
        return self.pushover.name

    def get_type(self):
        return CONFIG_NOTIFIER

    async def prepare(self):
        pass

    def notify(self, message):
        return self.pushover.notify(message=message, **self.service_config)

    def get_successful_startup_message(self):
        try:
            return f"Notifier successfully initialized, more info at: {self.pushover.site_url}.", True
        except Exception as e:
            self.log_connection_error_message(e)
            return "", False
