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


LOCAL_HOST_IP = "127.0.0.1"


class NodeApiService(services.AbstractService):
    BACKTESTING_ENABLED = True

    def __init__(self):
        super().__init__()
        self.api_app = None
        self.admin_username = None
        self.admin_password = None
        self.node_api_url = None
        self.node_sqlite_file = None
        self.node_redis_url = None

    def get_fields_description(self):
        return {
            services_constants.CONFIG_NODE_WEB_PORT: "Port to access the OctoBot Node web interface from.",
            services_constants.ADMIN_USERNAME: "Admin username (email format) for Node API basic authentication.",
            services_constants.ADMIN_PASSWORD: "Admin password for Node API basic authentication.",
            services_constants.NODE_API_URL: "Base URL used by the Node Web UI to reach the Node API.",
            services_constants.NODE_SQLITE_FILE: "SQLite database file path for the Node scheduler.",
            services_constants.NODE_REDIS_URL: "Redis URI for the Node scheduler (optional).",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_NODE_WEB_PORT: services_constants.DEFAULT_NODE_WEB_PORT,
            services_constants.ADMIN_USERNAME: "admin@example.com",
            services_constants.ADMIN_PASSWORD: "changethis",
            services_constants.NODE_API_URL: self._get_default_node_api_url(),
            services_constants.NODE_SQLITE_FILE: "tasks.db",
            services_constants.NODE_REDIS_URL: None,
        }

    def get_required_config(self):
        return [services_constants.CONFIG_NODE_WEB_PORT]

    @staticmethod
    def is_setup_correctly(config):
        return services_constants.CONFIG_NODE_WEB in config[services_constants.CONFIG_CATEGORY_SERVICES] \
               and services_constants.CONFIG_SERVICE_INSTANCE in config[services_constants.CONFIG_CATEGORY_SERVICES][
                   services_constants.CONFIG_NODE_WEB
               ]

    @staticmethod
    def get_is_enabled(config):
        # allow to disable node api interface from config, enabled by default otherwise
        try:
            return config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_NODE_WEB][
                commons_constants.CONFIG_ENABLED_OPTION
            ]
        except KeyError:
            return True

    def has_required_configuration(self):
        return self.get_is_enabled(self.config)

    def get_endpoint(self) -> None:
        return self.api_app

    def get_type(self) -> None:
        return services_constants.CONFIG_NODE_WEB

    @staticmethod
    def get_should_warn():
        return False

    async def stop(self):
        if self.api_app:
            self.api_app.stop()

    async def prepare(self) -> None:
        try:
            node_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_NODE_WEB]
            self.admin_username = node_config.get(services_constants.ADMIN_USERNAME)
            self.admin_password = node_config.get(services_constants.ADMIN_PASSWORD)
            self.node_api_url = node_config.get(services_constants.NODE_API_URL)
            self.node_sqlite_file = node_config.get(services_constants.NODE_SQLITE_FILE)
            self.node_redis_url = node_config.get(services_constants.NODE_REDIS_URL)
        except KeyError:
            self.admin_username = None
            self.admin_password = None
            self.node_api_url = None
            self.node_sqlite_file = None
            self.node_redis_url = None

        defaults = self.get_default_value()
        updated_config = {}
        if not self.admin_username:
            self.admin_username = defaults[services_constants.ADMIN_USERNAME]
            updated_config[services_constants.ADMIN_USERNAME] = self.admin_username
        if not self.admin_password:
            self.admin_password = defaults[services_constants.ADMIN_PASSWORD]
            updated_config[services_constants.ADMIN_PASSWORD] = self.admin_password
        if not self.node_api_url:
            self.node_api_url = defaults[services_constants.NODE_API_URL]
            updated_config[services_constants.NODE_API_URL] = self.node_api_url
        if not self.node_sqlite_file:
            self.node_sqlite_file = defaults[services_constants.NODE_SQLITE_FILE]
            updated_config[services_constants.NODE_SQLITE_FILE] = self.node_sqlite_file
        if self.node_redis_url is None:
            self.node_redis_url = defaults[services_constants.NODE_REDIS_URL]
            updated_config[services_constants.NODE_REDIS_URL] = self.node_redis_url

        if updated_config:
            self.save_service_config(services_constants.CONFIG_NODE_WEB, updated_config, update=True)

    def _get_default_node_api_url(self):
        port = self._get_node_web_server_port()
        return f"http://{LOCAL_HOST_IP}:{port}"

    def _get_node_web_server_port(self):
        try:
            return os.getenv(
                services_constants.ENV_NODE_WEB_PORT,
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_NODE_WEB][
                    services_constants.CONFIG_NODE_WEB_PORT
                ],
            )
        except KeyError:
            return os.getenv(services_constants.ENV_NODE_WEB_PORT, services_constants.DEFAULT_NODE_WEB_PORT)

    def _get_node_web_server_url(self):
        port = self._get_node_web_server_port()
        try:
            return f"{os.getenv(services_constants.ENV_NODE_WEB_ADDRESS, socket.gethostbyname(socket.gethostname()))}:{port}"
        except OSError as err:
            self.logger.warning(
                f"Impossible to find local node web interface url, using default instead: {err} ({err.__class__.__name__})"
            )
        return f"{LOCAL_HOST_IP}:{port}"

    def get_successful_startup_message(self):
        return f"Node API interface successfully initialized and accessible at: http://{self._get_node_web_server_url()}.", True

    def get_bind_host(self):
        return os.getenv(services_constants.ENV_NODE_WEB_ADDRESS, services_constants.DEFAULT_NODE_WEB_IP)

    def get_bind_port(self):
        return int(self._get_node_web_server_port())

    def get_admin_username(self):
        return os.getenv(services_constants.ENV_ADMIN_USERNAME, self.admin_username)

    def get_admin_password(self):
        return os.getenv(services_constants.ENV_ADMIN_PASSWORD, self.admin_password)

    def get_node_api_url(self):
        return self.node_api_url or self._get_default_node_api_url()

    def get_node_sqlite_file(self):
        return os.getenv(services_constants.ENV_NODE_SQLITE_FILE, self.node_sqlite_file)

    def get_node_redis_url(self):
        return os.getenv(services_constants.ENV_NODE_REDIS_URL, self.node_redis_url)
