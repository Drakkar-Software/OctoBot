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

import octobot_tentacles_manager.models.artifact as artifact
import octobot_tentacles_manager.constants as constants


class TentaclePackage(artifact.Artifact):
    ARTIFACT_NAME = "tentacle package"
    ARTIFACT_SUFFIX = "package"

    def __init__(self, name=None):
        super().__init__(name)
        self.artifacts: list = []
        self.parse_path_in_name_if_any()

    def add_artifact(self, new_artifact: artifact.Artifact) -> None:
        """
        Add a new artifact to the package
        Used to manage the artifact name :
        - If only one artifact is present in the package -> use its name and version
        - If more artifacts are present, use the first artifact's origin package as name
        :param new_artifact: the artifact to add
        :return: None
        """
        self.artifacts.append(new_artifact)
        if len(self.artifacts) == 1:
            self.name = self.artifacts[0].get_name_with_version()
        elif len(self.artifacts) > 1:
            self.name = self.get_package_default_name()

    def parse_path_in_name_if_any(self) -> None:
        """
        Parse path in package name if any
        :return: None
        """
        if self.name \
                and len(os.path.split(self.name)) > 1 \
                and (split_path := os.path.split(self.name))[0]:
            self.output_path = split_path[0]
            self.name = split_path[1]

    def get_package_default_name(self) -> str:
        """
        :return: the default package name as 'origin_package@version_package'
        """
        return f"{self.artifacts[0].origin_package}{constants.ARTIFACT_VERSION_SEPARATOR}" \
               f"{self.version}_{self.ARTIFACT_SUFFIX}"

    def __str__(self):
        str_rep = f"{self.name} {TentaclePackage.ARTIFACT_NAME} ["
        if self.is_valid():
            return f"version: {self.version}]"
        else:
            return f"{str_rep}]"
