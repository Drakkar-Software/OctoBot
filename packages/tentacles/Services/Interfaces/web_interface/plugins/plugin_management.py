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
import os.path

import octobot_commons.tentacles_management as tentacles_management
import octobot_commons.logging as logging
import tentacles.Services.Interfaces.web_interface.plugins as plugins


def register_all_plugins(server_instance, already_registered_plugins, **kwargs) -> list:
    registered_plugins = []
    already_registered_plugins_by_classes = {
        plugin.__class__: plugin
        for plugin in already_registered_plugins
    }
    for plugin_class in _get_all_plugins():
        try:
            can_use_plugin = True
            # flask blueprints can't be be unregistered: reuse them when already registered
            if plugin_class in already_registered_plugins_by_classes:
                plugin = already_registered_plugins_by_classes[plugin_class]
            else:
                plugin = plugin_class.factory(**kwargs)
                can_use_plugin = os.path.exists(plugin.plugin_folder)
                if can_use_plugin:
                    plugin.register(server_instance)
            if can_use_plugin:
                registered_plugins.append(plugin)
        except Exception as e:
            logging.get_logger("WebInterfacePluggingRegistration").exception(
                e,
                True,
                f"Error when registering {plugin_class.__name__} plugin: {e}"
            )
    return registered_plugins


def _get_all_plugins() -> list:
    return tentacles_management.get_all_classes_from_parent(plugins.AbstractWebInterfacePlugin)
