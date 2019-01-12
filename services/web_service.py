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
    REQUIRED_CONFIG = [CONFIG_WEB_PORT]

    # Used in configuration interfaces
    CONFIG_FIELDS_DESCRIPTION = {
        CONFIG_WEB_PORT: "Port to access your OctoBot web interface from."
    }
    CONFIG_DEFAULT_VALUE = {
        CONFIG_WEB_PORT: 5000
    }
    HELP_PAGE = "https://github.com/Drakkar-Software/OctoBot/wiki/Web-interface#web-interface"

    BACKTESTING_ENABLED = True

    def __init__(self):
        super().__init__()
        self.web_app = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_WEB in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB]

    @staticmethod
    def is_available(config):
        return WebService.is_setup_correctly(config) and \
               config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION]

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_WEB in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_ENABLED_OPTION]

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
