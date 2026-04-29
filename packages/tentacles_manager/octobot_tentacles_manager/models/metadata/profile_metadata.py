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
import octobot_tentacles_manager.models.metadata.artifact_metadata as artifact_metadata
import octobot_tentacles_manager.models.profile as profile_model


class ProfileMetadata(artifact_metadata.ArtifactMetadata):
    def __init__(self, artifact: profile_model.Profile):
        super().__init__(artifact)
        self.artifact_type: enums.ArtifactTypes = enums.ArtifactTypes.PROFILE
