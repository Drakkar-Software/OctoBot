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

import octobot_tentacles_manager.models.tentacle as tentacle_model
import octobot_tentacles_manager.models.tentacle_package as tentacle_package_model
import octobot_tentacles_manager.models.profile as profile_model

import octobot_tentacles_manager.models.metadata.tentacle_metadata as tentacle_metadata
import octobot_tentacles_manager.models.metadata.tentacle_package_metadata as tentacle_package_metadata
import octobot_tentacles_manager.models.metadata.profile_metadata as profile_metadata


class MetadataFactory:
    def __init__(self, artifact):
        self.artifact = artifact

    def create_metadata_instance(self):
        if isinstance(self.artifact, tentacle_model.Tentacle):
            return tentacle_metadata.TentacleMetadata(self.artifact)
        elif isinstance(self.artifact, tentacle_package_model.TentaclePackage):
            return tentacle_package_metadata.TentaclePackageMetadata(self.artifact)
        elif isinstance(self.artifact, profile_model.Profile):
            return profile_metadata.ProfileMetadata(self.artifact)
        return None
