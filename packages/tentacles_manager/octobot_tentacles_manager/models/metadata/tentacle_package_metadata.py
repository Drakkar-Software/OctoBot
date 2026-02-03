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
import octobot_tentacles_manager.enums as enums
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.models.tentacle_package as tentacle_package_model
import octobot_tentacles_manager.models.metadata.artifact_metadata as artifact_metadata


class TentaclePackageMetadata(artifact_metadata.ArtifactMetadata):
    def __init__(self, artifact: tentacle_package_model.TentaclePackage):
        super().__init__(artifact)
        self.artifact_type: enums.ArtifactTypes = enums.ArtifactTypes.TENTACLE_PACKAGE
        self.original_metadata_dict = None

    def load_from_dict(self) -> None:
        if self.original_metadata_dict:
            if self.original_metadata_dict.get(constants.ARTIFACT_METADATA_VERSION):
                self.artifact.version = self.original_metadata_dict.get(constants.ARTIFACT_METADATA_VERSION)

    def to_dict(self) -> dict:
        origin_dict = super().to_dict()
        origin_dict[constants.ARTIFACT_METADATA_TENTACLES] = [
            artifact.get_name_with_version() for artifact in self.artifact.artifacts
        ]
        if self.original_metadata_dict:
            origin_dict.update(self.original_metadata_dict)
        return origin_dict
