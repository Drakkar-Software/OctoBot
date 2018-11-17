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

from config import CONFIG_INTERFACES, CONFIG_ENABLED_OPTION
from tools.logging.logging_util import get_logger


class InterfaceBot:
    def __init__(self, config):
        self.config = config
        self.paused = False
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def enable(config, is_enabled, associated_config=None):
        if CONFIG_INTERFACES not in config:
            config[CONFIG_INTERFACES] = {}
        if associated_config not in config[CONFIG_INTERFACES]:
            config[CONFIG_INTERFACES][associated_config] = {}
        config[CONFIG_INTERFACES][associated_config][CONFIG_ENABLED_OPTION] = is_enabled

    @staticmethod
    def is_enabled(config, associated_config=None):
        return CONFIG_INTERFACES in config \
               and associated_config in config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][associated_config] \
               and config[CONFIG_INTERFACES][associated_config][CONFIG_ENABLED_OPTION]
