#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path


class TentacleType:
    def __init__(self, type_path: str, module_name: str = None):
        self.path: str = type_path
        self.module_name: str = module_name

    @staticmethod
    def from_import_path(root: str, import_path: str):
        """
        Create a tentacle type from a path
        :param root: the root path
        :param import_path: the import path
        :return: the created TentacleType instance
        """
        module_name = import_path.split(".")[-1]
        tentacle_type_path = import_path.split(f"{root}.")[-1]\
            .replace(f".{module_name}", "")\
            .replace(f".", path.sep)
        return TentacleType(tentacle_type_path, module_name)

    def is_of_type(self, required_type) -> bool:
        return required_type in self.path.split(path.sep)

    def get_last_element(self) -> str:
        """
        :return: the path last element
        """
        return self.path.split(path.sep)[-1]

    def get_root_type(self) -> str:
        """
        :return: the root type
        """
        return self.path.split(path.sep)[0]

    def to_path(self) -> str:
        """
        :return: the tentacle type path
        """
        return self.path

    def __str__(self) -> str:
        return self.path.replace(path.sep, ".")
