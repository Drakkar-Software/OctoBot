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

import octobot_tentacles_manager.models.artifact as artifact


class Profile(artifact.Artifact):
    ARTIFACT_NAME = "profile"

    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        str_rep: str = f"{self.name} {Profile.ARTIFACT_NAME} ["
        if self.is_valid():
            return f"{str_rep}version: {self.version}]"
        else:
            return f"{str_rep}]"
