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
from typing import List

import apprise

from config import PROJECT_NOTIFICATION, CONFIG_APPRISE, CONFIG_CATEGORY_SERVICES, CONFIG_SERVICE_INSTANCE
from services.abstract_service import AbstractService


class AppriseService(AbstractService):
    """
    Apprise package wrapper
    """
    def __init__(self):
        super().__init__()
        self.apprise_inst = apprise.Apprise()

    def register_service(self, service_name: str, config: List[str]):
        self.apprise_inst.add(f"{service_name}://{'/'.join(config)}")

    def get_fields_description(self):
        return {key: self.get_fields_description_from_schema(key)
                for key in self.get_required_config()}

    def get_default_value(self):
        return {key: ""
                for key in self.get_required_config()}

    def get_fields_description_from_schema(self, field):
        # _, desc = dict_util.find_nested_value(self.apprise_inst.details()[APPRISE_SCHEMA_KEY])
        return ""

    def get_required_config(self):
        required_list = []
        # self.apprise_inst.asset
        return required_list

    @classmethod
    def get_help_page(cls) -> str:
        return "https://github.com/Drakkar-Software/OctoBot/wiki/Apprise-interface#apprise-interface"

    def get_type(self):
        return CONFIG_APPRISE

    def get_endpoint(self):
        return self.apprise_inst

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_APPRISE in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_APPRISE]

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_APPRISE in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_APPRISE])

    async def prepare(self):
        # register_service TODO
        # self.register_service('pbul', ['o.gn5kj6nfhv736I7jC3cj3QLRiyhgl98b'])
        pass

    async def notify(self, message):
        return self.apprise_inst.notify(
            title=PROJECT_NOTIFICATION,
            body=message,
        )

    def get_successful_startup_message(self):
        try:
            return f"Apprise notifiers successfully initialized, more info at: #TODO", True
        except Exception as e:
            self.log_connection_error_message(e)
            return "", False
