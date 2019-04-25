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

import socket

from config import CONFIG_WEB, CONFIG_CATEGORY_SERVICES, CONFIG_ENABLED_OPTION, CONFIG_SERVICE_INSTANCE, \
    CONFIG_WEB_IP, CONFIG_WEB_PORT, DEFAULT_SERVER_IP, DEFAULT_SERVER_PORT
from interfaces.web.web_app import WebApp
from services import AbstractService


class WebService(AbstractService):
    BACKTESTING_ENABLED = True

    def __init__(self):
        super().__init__()
        self.web_app = None

    def get_fields_description(self):
        return {
            CONFIG_WEB_PORT: "Port to access your OctoBot web interface from."
        }

    def get_default_value(self):
        return {
            CONFIG_WEB_PORT: DEFAULT_SERVER_PORT
        }

    def get_required_config(self):
        return [CONFIG_WEB_PORT]

    @classmethod
    def get_help_page(cls) -> str:
        return "https://github.com/Drakkar-Software/OctoBot/wiki/Web-interface#web-interface"

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_WEB in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]

    # If this service is enabled
    def get_is_enabled(self, config):
        return super().get_is_enabled(config) and self._check_enabled_option(config)

    @staticmethod
    def _check_enabled_option(config):
        return CONFIG_CATEGORY_SERVICES in config \
            and CONFIG_WEB in config[CONFIG_CATEGORY_SERVICES] \
            and config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION]

    @staticmethod
    def is_available(config):
        return WebService.is_setup_correctly(config) and \
               config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION]

    def has_required_configuration(self):
        return self._check_enabled_option(self.config)

    def get_endpoint(self) -> None:
        return self.web_app

    def get_type(self) -> None:
        return CONFIG_WEB

    async def prepare(self) -> None:
        self.web_app = WebApp(self.config)
        self.web_app.start()

    @staticmethod
    def get_should_warn():
        return False

    def stop(self):
        if self.web_app:
            self.web_app.stop()

    @staticmethod
    def enable(config, is_enabled):
        if CONFIG_CATEGORY_SERVICES not in config:
            config[CONFIG_CATEGORY_SERVICES] = {}
        if CONFIG_WEB not in config[CONFIG_CATEGORY_SERVICES]:
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB] = {}
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP] = DEFAULT_SERVER_IP
            config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT] = DEFAULT_SERVER_PORT
        else:
            if CONFIG_WEB_IP not in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]:
                config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_IP] = DEFAULT_SERVER_IP
            if CONFIG_WEB_PORT not in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]:
                config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT] = DEFAULT_SERVER_PORT

        config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION] = is_enabled

    def _get_web_server_url(self):
        return f"{socket.gethostbyname(socket.gethostname())}:" \
               f"{self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT]}"

    def get_successful_startup_message(self):
        return f"Interface successfully initialized and accessible at: http://{self._get_web_server_url()}.", True
