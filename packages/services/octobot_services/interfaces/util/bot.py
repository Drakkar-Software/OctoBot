#  Drakkar-Software OctoBot-Services
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

import octobot_services.interfaces as interfaces


def get_bot_api():
    return interfaces.AbstractInterface.bot_api


def get_exchange_manager_ids():
    return get_bot_api().get_exchange_manager_ids()


def get_global_config():
    return get_bot_api().get_global_config()


def get_startup_config(dict_only=True):
    return get_bot_api().get_startup_config(dict_only=dict_only)


def get_edited_config(dict_only=True):
    return get_bot_api().get_edited_config(dict_only=dict_only)


def get_startup_tentacles_config():
    return get_bot_api().get_startup_tentacles_config()


def get_edited_tentacles_config():
    return get_bot_api().get_edited_tentacles_config()


def set_edited_tentacles_config(config):
    return get_bot_api().set_edited_tentacles_config(config)
