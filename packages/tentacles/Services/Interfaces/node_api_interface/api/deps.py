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

import octobot_node.models
import octobot.community.authentication as community_auth

security_basic = HTTPBasic(auto_error=False)

_BASIC_AUTH_USER_ID = uuid.uuid4()


def get_current_user(
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> octobot_node.models.User:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None or not auth.is_node_wallet_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not configured",
        )
    if credentials is None or not auth.verify_node_passphrase(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect passphrase",
        )
    address = auth.get_node_wallet_address()
    return octobot_node.models.User(
        id=_BASIC_AUTH_USER_ID,
        email=address,
        is_active=True,
        is_superuser=True,
        full_name=None,
    )


CurrentUser = typing.Annotated[octobot_node.models.User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> octobot_node.models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
