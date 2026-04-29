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

from octobot_tentacles_manager.uploaders import uploader
from octobot_tentacles_manager.uploaders.uploader import (
    Uploader,
)

from octobot_tentacles_manager.uploaders import nexus_uploader
from octobot_tentacles_manager.uploaders.nexus_uploader import (
    NexusUploader,
)

from octobot_tentacles_manager.uploaders import s3_uploader
from octobot_tentacles_manager.uploaders.s3_uploader import (
    S3Uploader,
)


__all__ = [
    "Uploader",
    "NexusUploader",
    "S3Uploader",
]
