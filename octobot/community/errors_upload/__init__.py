#  Drakkar-Software OctoBot-Commons
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

from octobot.community.errors_upload import initializer
from octobot.community.errors_upload.initializer import (
    register_error_uploader,
)
from octobot.community.errors_upload import error_model
from octobot.community.errors_upload.error_model import (
    Error,
)
from octobot.community.errors_upload import errors_uploader
from octobot.community.errors_upload.errors_uploader import (
    ErrorsUploader,
)

__all__ = [
    "register_error_uploader",
    "Error",
    "ErrorsUploader",
]
