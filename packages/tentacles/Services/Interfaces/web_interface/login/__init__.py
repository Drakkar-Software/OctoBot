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


from tentacles.Services.Interfaces.web_interface.login import user
from tentacles.Services.Interfaces.web_interface.login.user import (
    User,
)


from tentacles.Services.Interfaces.web_interface.login import web_login_manager
from tentacles.Services.Interfaces.web_interface.login.web_login_manager import (
    WebLoginManager,
    active_login_required,
    login_required_when_activated,
    register_attempt,
    is_banned,
    reset_attempts,
    set_is_login_required,
    is_login_required,
    is_authenticated,
    GENERIC_USER,
)


__all__ = [
    "User",
    "WebLoginManager",
    "active_login_required",
    "login_required_when_activated",
    "register_attempt",
    "is_banned",
    "reset_attempts",
    "set_is_login_required",
    "is_login_required",
    "is_authenticated",
    "GENERIC_USER",
]
