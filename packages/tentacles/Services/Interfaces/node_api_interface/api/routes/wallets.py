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

import octobot.community.authentication as community_auth
import octobot.community.wallet_backend as wallet_backend

try:
    from api.deps import CurrentUser, security_basic  # type: ignore[no-redef]
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser, security_basic

router = APIRouter(tags=["wallets"])


class WalletInfo(pydantic.BaseModel):
    address: str
    name: typing.Optional[str] = None
    is_admin: bool = False


class CreateWalletBody(pydantic.BaseModel):
    passphrase: str
    name: typing.Optional[str] = None
    private_key: typing.Optional[str] = None
    seed: typing.Optional[str] = None


class UpdateWalletBody(pydantic.BaseModel):
    name: typing.Optional[str] = None


@router.get("/", response_model=list[WalletInfo])
def list_wallets(
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
) -> list[WalletInfo]:
    """Return configured wallets (no auth required for login page).
    Names and is_admin are only revealed to verified callers to avoid PII disclosure."""
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        return []
    wallets_data = auth.list_wallets()
    # Gate is_admin behind credential verification; names are labels visible on login page
    reveal_admin = (
        credentials is not None
        and bool(credentials.username)
        and bool(credentials.password)
        and auth.verify_wallet_passphrase(credentials.username.lower(), credentials.password)
    )
    return [
        WalletInfo(
            address=w.address,
            name=w.name if reveal_admin else None,
            is_admin=w.is_admin if reveal_admin else False,
        )
        for w in wallets_data
    ]


@router.post("/", response_model=WalletInfo)
def create_wallet(body: CreateWalletBody, current_user: CurrentUser) -> WalletInfo:
    """Add a new wallet (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the admin wallet can add wallets",
        )
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    try:
        if body.private_key:
            wallet = auth.import_wallet(
                private_key=body.private_key,
                passphrase=body.passphrase,
                name=body.name,
                is_admin=False,
            )
        elif body.seed:
            wallet = auth.import_wallet_from_seed(
                seed=body.seed,
                passphrase=body.passphrase,
                name=body.name,
                is_admin=False,
            )
        else:
            wallet = auth.create_wallet(
                name=body.name,
                passphrase=body.passphrase,
                is_admin=False,
            )
    except wallet_backend.WalletError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
    return WalletInfo(address=wallet.address, name=body.name or None, is_admin=False)


@router.patch("/{address}", response_model=WalletInfo)
def update_wallet(address: str, body: UpdateWalletBody, current_user: CurrentUser) -> WalletInfo:
    """Rename a wallet (admin only)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the admin wallet can rename wallets",
        )
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    normalized = address.lower()
    try:
        auth.rename_wallet(normalized, body.name)
    except wallet_backend.WalletNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    return WalletInfo(
        address=normalized,
        name=body.name or None,
        is_admin=auth.is_admin_wallet(normalized),
    )


@router.delete("/{address}")
def delete_wallet(address: str, current_user: CurrentUser) -> dict:
    """Remove a wallet (admin only). Orphaned tasks remain visible to admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the admin wallet can remove wallets",
        )
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized",
        )
    normalized = address.lower()
    try:
        auth.remove_wallet(normalized)
    except wallet_backend.WalletNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except (wallet_backend.CannotRemoveLastWalletError, wallet_backend.CannotRemoveAdminWalletError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err
    return {"address": normalized}
