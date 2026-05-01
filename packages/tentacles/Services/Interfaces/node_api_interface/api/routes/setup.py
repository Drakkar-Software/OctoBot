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

import typing

import pydantic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials

import octobot_node.config as node_config
import octobot.community.authentication as community_auth
import octobot.community.wallet_backend as wallet_backend

try:
    from api.deps import CurrentUser, security_basic  # type: ignore[no-redef]
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser, security_basic

router = APIRouter(tags=["setup"])


class SetupStatus(pydantic.BaseModel):
    configured: bool


class SetupInit(pydantic.BaseModel):
    passphrase: str
    node_type: typing.Literal["standalone", "master"]
    private_key: typing.Optional[str] = None
    name: typing.Optional[str] = None


class SetupResult(pydantic.BaseModel):
    address: str


class WalletExport(pydantic.BaseModel):
    address: str
    private_key: str


@router.get("/setup/status", response_model=SetupStatus)
def get_setup_status() -> SetupStatus:
    auth = community_auth.CommunityAuthentication.instance()
    configured = auth is not None and (auth.is_node_wallet_configured() or bool(auth.list_wallets()))
    return SetupStatus(configured=configured)


@router.post("/setup/init", response_model=SetupResult)
def init_setup(body: SetupInit) -> SetupResult:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    already_configured = auth.is_node_wallet_configured() or bool(auth.list_wallets())
    if already_configured:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is already configured",
        )
    try:
        if body.private_key:
            wallet = auth.import_wallet(
                private_key=body.private_key,
                passphrase=body.passphrase,
                name=body.name,
                is_admin=True,
            )
        else:
            wallet = auth.create_wallet(
                name=body.name,
                passphrase=body.passphrase,
                is_admin=True,
            )
    except (wallet_backend.WalletAlreadyExistsError, wallet_backend.AdminWalletAlreadyExistsError) as err:
        # A concurrent request already configured the node — surface 409.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err
    except wallet_backend.WalletError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    node_config.settings.IS_MASTER_MODE = body.node_type == "master"
    return SetupResult(address=wallet.address)


@router.get("/setup/wallet/export", response_model=WalletExport)
def export_wallet(
    current_user: CurrentUser,
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> WalletExport:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None or credentials is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not configured",
        )
    try:
        wallet = auth.decrypt_wallet_by_address(current_user.email, credentials.password)
    except wallet_backend.WalletNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet not found",
        )
    except wallet_backend.WalletError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passphrase",
        )
    return WalletExport(address=wallet.address, private_key=wallet.private_key)
