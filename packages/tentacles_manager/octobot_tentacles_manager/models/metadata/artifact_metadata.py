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
import octobot_tentacles_manager.models.artifact as artifact_model


class ArtifactMetadata:
    def __init__(self, artifact: artifact_model.Artifact):
        self.artifact: artifact_model.Artifact = artifact
        self.version: str = self.artifact.version
        self.author: str = constants.DEFAULT_ARTIFACT_METADATA_AUTHOR
        self.artifact_type: enums.ArtifactTypes = None

    def to_dict(self) -> dict:
        return {
            constants.ARTIFACT_METADATA_NAME: self.artifact.name,
            constants.ARTIFACT_METADATA_SHORT_NAME: self.artifact.name,
            constants.ARTIFACT_METADATA_VERSION: self.artifact.version,
            constants.ARTIFACT_METADATA_ARTIFACT_TYPE: self.artifact_type.value,
            constants.ARTIFACT_METADATA_REPOSITORY: self.artifact.origin_repository,
            constants.ARTIFACT_METADATA_AUTHOR: self.author,
            constants.ARTIFACT_METADATA_DESCRIPTION: "",
            constants.ARTIFACT_METADATA_TAGS: [],
        }
