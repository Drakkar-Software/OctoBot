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
import json
import os.path as path

import typing
import aiofiles

import octobot_tentacles_manager.models.artifact as artifact
import octobot_tentacles_manager.constants as constants
import octobot_commons.json_util as json_util


class Tentacle(artifact.Artifact):
    ARTIFACT_NAME = "tentacle"

    def __init__(self, tentacle_root_path, name, tentacle_type, tentacle_class_names=None):
        super().__init__(name)
        self.tentacle_root_path = tentacle_root_path
        self.tentacle_type = tentacle_type
        self.tentacle_root_type = self.tentacle_type.get_root_type()
        self.tentacle_path = path.join(self.tentacle_root_path, self.tentacle_type.to_path())
        self.tentacle_module_path = None
        self.tentacle_class_names = tentacle_class_names or []
        self.tentacles_requirements = None
        self.tentacle_group = self.name
        self.in_dev_mode = False
        self.build_command: typing.Optional[typing.List[str]] = None
        self.include_patterns: typing.Optional[typing.List[str]] = None
        self.metadata = {}

    async def initialize(self) -> None:
        """
        Initialize a tentacle object with its metadata file
        :return: None
        """
        self.tentacle_module_path = path.join(self.tentacle_path, self.name)
        async with aiofiles.open(path.join(self.tentacle_module_path,
                                           constants.TENTACLE_METADATA), "r") as metadata_file:
            self._read_metadata_dict(json.loads(await metadata_file.read()))

    def sync_initialize(self) -> None:
        """
        Initialize synchronously a tentacle object with its metadata file
        :return: None
        """
        try:
            self.tentacle_module_path = path.join(self.tentacle_path, self.name)
            file_path = path.join(self.tentacle_path, self.name, constants.TENTACLE_METADATA)
            self._read_metadata_dict(json_util.read_file(file_path))
        except FileNotFoundError:
            pass

    @staticmethod
    def find(iterable, name) -> object:
        """
        Find a tentacle from an iterable
        :param iterable: the iterable
        :param name: the tentacle name
        :return: the tentacle if found else None
        """
        for tentacle in iterable:
            if tentacle.name == name:
                return tentacle
        return None

    def get_simple_tentacle_type(self) -> str:
        """
        :return: the tentacle type from its folder in tentacle files architecture
        """
        return self.tentacle_type.get_last_element()

    def __str__(self) -> str:
        str_rep: str = f"{self.name} {Tentacle.ARTIFACT_NAME} [type: {self.tentacle_type}"
        if self.is_valid():
            return f"{str_rep}, version: {self.version}]"
        else:
            return f"{str_rep}]"

    def extract_tentacle_requirements(self) -> list:
        """
        :return: The tentacle requirement list
        """
        return [self._parse_requirements(component) for component in self.tentacles_requirements]

    def _read_metadata_dict(self, metadata: dict) -> None:
        """
        Load tentacle metadata from its dict
        :param metadata: the tentacle metadata dict
        :return: None
        """
        self.metadata = metadata
        self.version = self.metadata[constants.METADATA_VERSION]
        self.origin_package = self.metadata[constants.METADATA_ORIGIN_PACKAGE]
        self.tentacle_class_names = self.metadata[constants.METADATA_TENTACLES]
        self.tentacles_requirements = self.metadata[constants.METADATA_TENTACLES_REQUIREMENTS]
        # self.tentacle_group is this tentacle name if no provided
        self.tentacle_group = self.metadata.get(constants.METADATA_TENTACLES_GROUP, self.name)
        if constants.METADATA_DEV_MODE in self.metadata:
            self.in_dev_mode = self.metadata[constants.METADATA_DEV_MODE]
        # Read optional build command
        self.build_command = self.metadata.get(constants.METADATA_BUILD, None)
        # Read optional include patterns
        self.include_patterns = self.metadata.get(constants.METADATA_INCLUDE, None)

    @staticmethod
    def _parse_requirements(requirement) -> list:
        """
        Parse tentacle requirements
        :param requirement: tentacle requirements
        :return: parsed tentacle requirements
        """
        if constants.TENTACLE_REQUIREMENT_VERSION_EQUALS in requirement:
            return requirement.split(constants.TENTACLE_REQUIREMENT_VERSION_EQUALS)
        else:
            return [requirement, None]
