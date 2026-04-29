#  Drakkar-Software OctoBot-Interfaces
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
import flask
import os

import octobot_commons.enums as commons_enums
import octobot_commons.logging as logging
import octobot_commons.tentacles_management as tentacles_management
import octobot_tentacles_manager.api
import octobot_services.interfaces.util as interfaces_util


class AbstractWebInterfacePlugin(tentacles_management.AbstractTentacle):
    USER_INPUT_TENTACLE_TYPE = commons_enums.UserInputTentacleTypes.WEB_PLUGIN
    NAME = None
    URL_PREFIX = None
    PLUGIN_ROOT_FOLDER = None
    TEMPLATE_FOLDER_NAME = "templates"
    STATIC_FOLDER_NAME = "static"
    ADDITIONAL_KWARGS = {}

    def __init__(self, name, url_prefix, plugin_folder, template_folder, static_folder, **kwargs):
        super().__init__()
        self.name = name
        self.url_prefix = url_prefix
        self.plugin_folder = plugin_folder
        self.template_folder = os.path.join(plugin_folder, template_folder) if plugin_folder else None
        self.static_folder = os.path.join(plugin_folder, static_folder) if plugin_folder else None
        self.kwargs = kwargs
        self.blueprint = None
        self.logger = logging.get_logger(self.name)

    @classmethod
    def get_name(cls):
        return cls.__name__

    def register_routes(self):
        raise NotImplementedError("register_routes is not implemented")

    def get_tabs(self):
        """
        Override if tabs are to be registered from this plugin
        :return:
        """
        return []

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        """
        Override if user inputs are required for this plugin
        """

    @classmethod
    def is_configurable(cls):
        """
        Override if the tentacle is allowed to be configured
        """
        return False

    def blueprint_factory(self):
        self.blueprint = flask.Blueprint(
            self.name,
            self.name,
            url_prefix=self.url_prefix,
            template_folder=self.template_folder,
            static_folder=self.static_folder,
            ** self.kwargs
        )
        return self.blueprint

    @classmethod
    def factory(cls, **kwargs):
        if cls.NAME is None:
            raise RuntimeError(f"{cls.__name__}.NAME mush be set")
        return cls(
            cls.NAME,
            cls.URL_PREFIX or f"/{cls.NAME}",
            cls.PLUGIN_ROOT_FOLDER,
            cls.TEMPLATE_FOLDER_NAME,
            cls.STATIC_FOLDER_NAME,
            **{**cls.ADDITIONAL_KWARGS, **kwargs}
        )

    def register(self, server_instance):
        self.blueprint_factory()
        self.register_routes()
        server_instance.register_blueprint(self.blueprint)
        self.logger.debug(f"Registered {self.name} plugin")

    @classmethod
    def get_tentacle_config(cls, tentacles_setup_config=None):
        return octobot_tentacles_manager.api.get_tentacle_config(
            tentacles_setup_config or interfaces_util.get_edited_tentacles_config(), cls
        )

    def __str__(self):
        return f"name: {self.name} url_prefix: {self.url_prefix} " \
               f"template_folder: {self.template_folder} static_folder: {self.static_folder}" \
               f"kwargs: {self.kwargs}"
