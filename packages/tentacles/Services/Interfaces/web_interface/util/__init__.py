#  Drakkar-Software OctoBot-Interfaces
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

from tentacles.Services.Interfaces.web_interface.util import flask_util
from tentacles.Services.Interfaces.web_interface.util.flask_util import (
    get_rest_reply,
)
from tentacles.Services.Interfaces.web_interface.util import browser_util
from tentacles.Services.Interfaces.web_interface.util.browser_util import (
    open_in_background_browser,
)

__all__ = [
    "get_rest_reply",
    "open_in_background_browser",
]
