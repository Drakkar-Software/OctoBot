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
import octobot.community.node_journal as node_journal
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.recording_context as journal_recording_context

try:
    from api.deps import CurrentUser, security_basic  # type: ignore[no-redef]
    from core import network
except ImportError:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser, security_basic
    from tentacles.Services.Interfaces.node_api_interface.core import network

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
    seed: typing.Optional[str] = None


class LocalNetworkAddress(pydantic.BaseModel):
    local_network_ip: typing.Optional[str] = None


class VPNNetworkAddress(pydantic.BaseModel):
    vpn_network_ip: typing.Optional[str] = None


@router.get("/setup/status", response_model=SetupStatus)
def get_setup_status() -> SetupStatus:
    auth = community_auth.CommunityAuthentication.instance()
    configured = auth is not None and auth.is_node_wallet_configured()
    return SetupStatus(configured=configured)


@router.get("/setup/local-network-address", response_model=LocalNetworkAddress)
def get_local_network_address() -> LocalNetworkAddress:
    return LocalNetworkAddress(local_network_ip=network.get_local_network_ip())


@router.get("/setup/vpn-network-address", response_model=VPNNetworkAddress)
def get_vpn_network_address() -> VPNNetworkAddress:
    return VPNNetworkAddress(vpn_network_ip=network.get_vpn_network_ip())


@router.post("/setup/init", response_model=SetupResult)
def init_setup(body: SetupInit) -> SetupResult:
    auth = community_auth.CommunityAuthentication.instance()
    setup_method = journal_enums.WalletSetupMethod.IMPORT if body.private_key else journal_enums.WalletSetupMethod.CREATE
    if auth is None:
        journal_recording_context.raise_wallet_setup_http_error(
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            failure_reason=journal_enums.WalletSetupFailureReason.SERVICE_UNAVAILABLE,
            setup_method=setup_method,
            detail="Service not initialized",
            error_message="Service not initialized",
        )
    if auth.list_wallets():
        journal_recording_context.raise_wallet_setup_http_error(
            http_status=status.HTTP_409_CONFLICT,
            failure_reason=journal_enums.WalletSetupFailureReason.ALREADY_CONFIGURED,
            setup_method=setup_method,
            detail="Node is already configured",
            error_message="Node is already configured",
        )
    node_journal.record_wallet_setup_attempt(
        node_type=body.node_type,
        setup_method=setup_method,
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
        journal_recording_context.raise_wallet_setup_http_error(
            http_status=status.HTTP_409_CONFLICT,
            failure_reason=journal_enums.WalletSetupFailureReason.CONCURRENT_RACE,
            setup_method=setup_method,
            detail=str(err),
            error=err,
        )
    except wallet_backend.WalletError as err:
        journal_recording_context.raise_wallet_setup_http_error(
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            failure_reason=journal_enums.WalletSetupFailureReason.WALLET_ERROR,
            setup_method=setup_method,
            detail=str(err),
            error=err,
        )
    node_config.settings.IS_MASTER_MODE = body.node_type == "master"
    node_journal.record_wallet_setup_succeeded()
    return SetupResult(address=wallet.address)


@router.get("/setup/wallet/export", response_model=WalletExport)
def export_wallet(
    current_user: CurrentUser,
    credentials: typing.Annotated[typing.Optional[HTTPBasicCredentials], Depends(security_basic)],
    address: typing.Optional[str] = None,
    passphrase: typing.Optional[str] = None,
) -> WalletExport:
    auth = community_auth.CommunityAuthentication.instance()
    if auth is None or credentials is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node not configured",
        )
    target_address = (address or current_user.email).lower()
    is_own_wallet = target_address == current_user.email.lower()
    if not is_own_wallet and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the admin can export other wallets",
        )
    target_passphrase = credentials.password if is_own_wallet else passphrase
    if not target_passphrase:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passphrase required",
        )
    try:
        entry = auth.decrypt_wallet_entry_by_address(target_address, target_passphrase)
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
    return WalletExport(address=entry.address, private_key=entry.private_key, seed=entry.seed or None)
