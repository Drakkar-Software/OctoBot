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

from config import CONFIG_CATEGORY_SERVICES, CONFIG_NOTIFIER_IGNORE, CONFIG_NOTIFIER, CONFIG_SERVICE_INSTANCE
from services.notifier_service import NotifierService


class NotifierServiceFactory:
    def __init__(self, config):
        self.config = config
        self.config[CONFIG_CATEGORY_SERVICES][CONFIG_NOTIFIER] = {CONFIG_SERVICE_INSTANCE: []}

    def create_services(self):
        for service_to_create in self.get_service_key_to_be_created():
            notifier_provider = NotifierService.is_available(service_to_create)
            if notifier_provider:
                notification_service = NotifierService
                notification_service.NOTIFIER_PROVIDER_TYPE = notifier_provider
                notification_service.SERVICE_CONFIG = self.config[CONFIG_CATEGORY_SERVICES][service_to_create]
                yield notification_service

    def get_service_key_to_be_created(self):
        return [key if key not in CONFIG_NOTIFIER_IGNORE else None
                for key in self.config[CONFIG_CATEGORY_SERVICES]]

    @staticmethod
    def get_notifiers_instance(config):
        if CONFIG_NOTIFIER in config[CONFIG_CATEGORY_SERVICES] \
           and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_NOTIFIER]:
            return config[CONFIG_CATEGORY_SERVICES][CONFIG_NOTIFIER][CONFIG_SERVICE_INSTANCE]
        return []
