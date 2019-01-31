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

from config import CONFIG_CATEGORY_SERVICES, PROJECT_NOTIFICATION, NOTIFIER_REQUIRED_KEY, \
    NOTIFIER_IGNORED_REQUIRED_CONFIG, NOTIFIER_REQUIRED_CONFIG, NOTIFIER_PROPERTIES_KEY
from services.abstract_service import AbstractService
from tools import dict_util


class NotifierService(AbstractService):
    NOTIFIER_PROVIDER_TYPE = None
    SERVICE_CONFIG = None

    def __init__(self):
        super().__init__()
        self.notifier_provider = self.__class__.NOTIFIER_PROVIDER_TYPE
        self.provider_name = self.notifier_provider.name
        self.service_config = self.__class__.SERVICE_CONFIG

    @classmethod
    def get_name(cls):
        return f"{cls.__name__}[{cls.NOTIFIER_PROVIDER_TYPE.name}]"

    def get_fields_description(self):
        return {key: self.get_fields_description_from_schema(key)
                for key in self.get_required_config()}

    def get_default_value(self):
        return {key: ""
                for key in self.get_required_config()}

    def get_fields_description_from_schema(self, field):
        _, desc = dict_util.find_nested_value(self.notifier_provider.schema[NOTIFIER_PROPERTIES_KEY][field], "title")
        return desc

    def get_required_config(self):
        required_list = []
        if NOTIFIER_REQUIRED_KEY in self.notifier_provider.required:
            required_list = self.notifier_provider.required[NOTIFIER_REQUIRED_KEY]
        if NOTIFIER_IGNORED_REQUIRED_CONFIG in required_list:
            required_list.remove(NOTIFIER_IGNORED_REQUIRED_CONFIG)
        if self.get_provider_name() in NOTIFIER_REQUIRED_CONFIG:
            required_list = set(required_list + NOTIFIER_REQUIRED_CONFIG[self.get_provider_name()])
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
        return self.provider_name

    def get_type(self):
        return self.provider_name

    async def prepare(self):
        pass

    async def notify(self, message):
        return self.notifier_provider.notify(message=message, subject=PROJECT_NOTIFICATION, **self.service_config)

    def get_successful_startup_message(self):
        try:
            return f"{self.get_provider_name()} notifier successfully initialized, more info at: " \
                       f"{self.notifier_provider.site_url}.", True
        except Exception as e:
            self.log_connection_error_message(e)
            return "", False
