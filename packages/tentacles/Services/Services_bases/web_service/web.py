#  Drakkar-Software OctoBot-Tentacles
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

import os
import socket

import octobot_commons.constants as commons_constants
import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot.constants as constants


LOCAL_HOST_IP = "127.0.0.1"


class WebService(services.AbstractService):
    def __init__(self):
        super().__init__()
        self.web_app = None
        self.requires_password = None
        self.password_hash = None

    def get_fields_description(self):
        return {
            services_constants.CONFIG_WEB_PORT: "Port to access your OctoBot web interface from.",
            services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: "When enabled, OctoBot will open the web interface on your web "
                                                                "browser upon startup.",
            services_constants.CONFIG_WEB_REQUIRES_PASSWORD: "When enabled, OctoBot web interface will be protected by a password. "
                                                             "Failing 10 times to enter this password will block the user and require "
                                                             "OctoBot to restart before being able to retry to authenticate.",
            services_constants.CONFIG_WEB_PASSWORD: "Password to enter to access this OctoBot when password protection is enabled. "
                                                    "Only a hash of this password will be stored."
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_WEB_PORT: services_constants.DEFAULT_SERVER_PORT,
            services_constants.CONFIG_AUTO_OPEN_IN_WEB_BROWSER: True,
            services_constants.CONFIG_WEB_REQUIRES_PASSWORD: False,
            services_constants.CONFIG_WEB_PASSWORD: ""
        }

    def get_required_config(self):
        return [services_constants.CONFIG_WEB_PORT]

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/web"

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_WEB in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_WEB]

    @staticmethod
    def get_is_enabled(config):
        # allow to disable web interface from config, enabled by default otherwise
        try:
            return config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                commons_constants.CONFIG_ENABLED_OPTION]
        except KeyError:
            return True

    def has_required_configuration(self):
        return self.get_is_enabled(self.config)

    def get_endpoint(self) -> None:
        return self.web_app

    def get_type(self) -> None:
        return services_constants.CONFIG_WEB

    def get_website_url(self):
        return "/home"

    def get_logo(self):
        return "static/img/svg/octobot.svg"

    async def prepare(self) -> None:
        try:
            self.requires_password = \
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                    services_constants.CONFIG_WEB_REQUIRES_PASSWORD]
            self.password_hash = \
            self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                services_constants.CONFIG_WEB_PASSWORD]
        except KeyError:
            if self.requires_password is None:
                self.requires_password = self.get_default_value()[services_constants.CONFIG_WEB_REQUIRES_PASSWORD]
            if self.password_hash is None:
                self.password_hash = self.get_default_value()[services_constants.CONFIG_WEB_PASSWORD]
            # save new values into config file
            updated_config = {
                services_constants.CONFIG_WEB_REQUIRES_PASSWORD: self.requires_password,
                services_constants.CONFIG_WEB_PASSWORD: self.password_hash
            }
            self.save_service_config(services_constants.CONFIG_WEB, updated_config, update=True)

    @staticmethod
    def get_should_warn():
        return False

    async def stop(self):
        if self.web_app:
            self.web_app.stop()

    def _get_web_server_port(self):
        try:
            return os.getenv(
                services_constants.ENV_WEB_PORT,
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_WEB][
                    services_constants.CONFIG_WEB_PORT]
            )
        except KeyError:
            return os.getenv(services_constants.ENV_WEB_PORT, services_constants.DEFAULT_SERVER_PORT)

    def _get_web_server_url(self):
        port = self._get_web_server_port()
        try:
            return f"{os.getenv(services_constants.ENV_WEB_ADDRESS, socket.gethostbyname(socket.gethostname()))}:{port}"
        except OSError as err:
            self.logger.warning(
                f"Impossible to find local web interface url, using default instead: {err} ({err.__class__.__name__})"
            )
        # use localhost by default
        return f"{LOCAL_HOST_IP}:{port}"

    def get_successful_startup_message(self):
        return f"Interface successfully initialized and accessible at: http://{self._get_web_server_url()}.", True
