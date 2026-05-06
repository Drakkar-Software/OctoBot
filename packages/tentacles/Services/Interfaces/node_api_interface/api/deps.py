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
import octobot.community.wallet_backend as wallet_backend

security_basic = HTTPBasic(auto_error=False)


def get_current_user(
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> octobot_node.models.User:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not configured",
        )

    # Multi-wallet path: username = wallet address, password = passphrase
    if credentials is None or not credentials.username:
        # Check whether the node is configured at all (no credentials → can't auth anyway)
        if not auth.list_wallets():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Node not configured",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet address required as username",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Normalize to lowercase so wallet_address == task.wallet_address always
    wallet_address = credentials.username.lower()
    passphrase = credentials.password
    if not passphrase:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passphrase required",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        wallet_info = auth.authenticate_wallet(wallet_address, passphrase)
    except wallet_backend.WalletError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect address or passphrase",
            headers={"WWW-Authenticate": "Basic"},
        )

    auth.init_sync_client_for_wallet(wallet_address)

    return octobot_node.models.User(
        id=uuid.uuid5(uuid.NAMESPACE_URL, wallet_address),
        email=wallet_address,
        is_active=True,
        is_superuser=wallet_info.is_admin,
        full_name=wallet_info.name,
    )


CurrentUser = typing.Annotated[octobot_node.models.User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> octobot_node.models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
