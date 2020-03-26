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
import copy


class ConfigurationManager:
    def __init__(self):
        self.configuration_elements = {}

    def add_element(self, key, element):
        self.configuration_elements[key] = ConfigurationElement(element)

    def get_edited_config(self, key):
        return self.configuration_elements[key].edited_config

    def get_startup_config(self, key):
        return self.configuration_elements[key].startup_config


class ConfigurationElement:
    def __init__(self, element):
        self.config = element
        self.startup_config = copy.deepcopy(element)
        self.edited_config = copy.deepcopy(element)
