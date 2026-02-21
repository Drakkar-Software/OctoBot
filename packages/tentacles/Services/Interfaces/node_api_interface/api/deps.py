#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import uuid
import typing

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import octobot_node.config
import octobot_node.models

security_basic = HTTPBasic()

_BASIC_AUTH_USER_ID = uuid.uuid4()

# TODO: support other auth methods (like supabase, jwt, etc.)

def get_current_user(credentials: typing.Annotated[HTTPBasicCredentials, Depends(security_basic)]) -> octobot_node.models.User:
    if credentials.username != octobot_node.config.settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if credentials.password != octobot_node.config.settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    user = octobot_node.models.User(
        id=_BASIC_AUTH_USER_ID,
        email=octobot_node.config.settings.ADMIN_USERNAME,
        is_active=True,
        is_superuser=True,
        full_name=None,
    )
    return user


CurrentUser = typing.Annotated[octobot_node.models.User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> octobot_node.models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
