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
import os

import octobot_tentacles_manager.models as models


class TentacleFactory:
    def __init__(self, tentacle_root_path, import_root_name=None):
        """
        :param tentacle_root_path: The file system path where tentacles are located
        :param import_root_name: The root name used in Python import paths (e.g., "tentacles").
                                 If None, defaults to the last component of tentacle_root_path.
                                 This is useful when the import path differs from the file path,
                                 e.g., when tentacles are installed to "packages/x/tests/tentacles"
                                 but imported as "tentacles.X.Y".
        """
        self.tentacle_root_path = tentacle_root_path
        # Use the last path component as import root if not specified
        self.import_root_name = import_root_name or os.path.basename(tentacle_root_path)

    def create_tentacle_from_type(self, name, tentacle_type, tentacle_class_names=None) -> models.Tentacle:
        """
        Create a tentacle artifact from its name and type
        :param name: the tentacle name
        :param tentacle_type: the tentacle type
        :param tentacle_class_names: list of tentacles classes names
        :return: the created TentacleArtifact instance
        """
        return models.Tentacle(self.tentacle_root_path, name, tentacle_type, tentacle_class_names=tentacle_class_names)

    async def create_and_load_tentacle_from_module(self, tentacle_module) -> models.Tentacle:
        """
        Create and load a tentacle from a tentacle module
        :param tentacle_module: the tentacle module to use
        :return: the loaded tentacle instance
        """
        # Use import_root_name for parsing import paths (e.g., "tentacles.X.Y")
        tentacle_type = models.TentacleType.from_import_path(self.import_root_name, tentacle_module.__name__)
        # Use tentacle_root_path for file system access
        tentacle = models.Tentacle(self.tentacle_root_path, tentacle_type.module_name, tentacle_type)
        await tentacle.initialize()
        return tentacle
