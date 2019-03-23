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


from tools.config_manager import ConfigManager


bot_instance = None
global_config = None
reference_market = None
default_time_frame = None


def __init__(bot, config):
    global bot_instance
    bot_instance = bot

    global global_config
    global_config = config


def get_bot():
    return bot_instance


def get_global_config():
    return global_config


def set_default_time_frame(time_frame):
    global default_time_frame
    default_time_frame = time_frame


def get_default_time_frame():
    return default_time_frame


def get_reference_market():
    global reference_market
    if reference_market is None:
        try:
            reference_market = ConfigManager.get_reference_market(global_config)
        except StopIteration:
            reference_market = None
    return reference_market
