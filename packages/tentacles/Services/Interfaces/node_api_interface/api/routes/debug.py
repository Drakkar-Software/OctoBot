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

import json
import typing

from fastapi import APIRouter, Body, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse

import octobot_node.config
import octobot_node.models
import octobot_node.protocol.debug as debug_protocol
import octobot_node.protocol.user_actions as user_actions_protocol
import octobot_node.scheduler
import octobot_protocol.models as protocol_models
import octobot_sync.server as _sync_server
import octobot.community.authentication as _community_auth

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser  # type: ignore[no-redef]
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]

router = APIRouter(tags=["debug"])


def _parse_user_action_payload(payload: typing.Any) -> protocol_models.UserAction:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be a JSON object",
        )
    try:
        user_action = protocol_models.UserAction.from_dict(payload)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if user_action is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user action payload",
        )
    if (
        user_action.configuration is None
        or user_action.configuration.actual_instance is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User action configuration is required",
        )
    return user_action


def _resolve_wallet_address(
    current_user: octobot_node.models.User,
    wallet_address: typing.Optional[str],
) -> str:
    """Return the resolved EVM wallet address (normalized to lowercase)."""
    if wallet_address is None:
        return current_user.email
    normalized_wallet_address = wallet_address.lower()
    if normalized_wallet_address == current_user.email.lower():
        return normalized_wallet_address
    if current_user.is_superuser:
        return normalized_wallet_address
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Wallet address does not belong to the authenticated user",
    )


def _resolve_user_id(
    current_user: octobot_node.models.User,
    wallet_address: typing.Optional[str],
) -> str:
    """Resolve EVM wallet address to the Starfish user_id used by the sync-core.

    The HTTP debug API accepts the EVM address for user-facing consistency, but all
    internal protocol and scheduler calls use the Starfish user_id.
    """
    evm_address = _resolve_wallet_address(current_user, wallet_address)
    wallet = _community_auth.CommunityAuthentication.instance().get_wallet(evm_address)
    return _sync_server.derive_user_id(wallet.private_key)


def _ensure_debug_routes_enabled() -> None:
    if octobot_node.config.settings.is_node_side_encryption_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug routes are disabled when node-side encryption is enabled",
        )


def _ensure_scheduler_initialized() -> None:
    if not octobot_node.scheduler.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized",
        )


@router.get("/", response_model=protocol_models.DebugState)
async def get_debug(
    current_user: CurrentUser,
    wallet_address: typing.Optional[str] = Query(default=None),
) -> JSONResponse:
    """Return debug state for a wallet.

    Requires authenticated user (``CurrentUser`` / HTTP Basic wallet + passphrase).
    Missing or invalid credentials return 401.
    """
    _ensure_debug_routes_enabled()
    _ensure_scheduler_initialized()
    resolved_user_id = _resolve_user_id(current_user, wallet_address)
    debug_state = await debug_protocol.get_debug_state(resolved_user_id)
    return JSONResponse(content=json.loads(debug_state.to_json()))


@router.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def execute_user_action(
    payload: typing.Annotated[typing.Any, Body()],
    current_user: CurrentUser,
    wallet_address: typing.Optional[str] = Query(default=None),
) -> Response:
    """Execute a user action for a wallet.

    Requires authenticated user (``CurrentUser`` / HTTP Basic wallet + passphrase).
    Missing or invalid credentials return 401.
    """
    _ensure_debug_routes_enabled()
    _ensure_scheduler_initialized()
    user_action = _parse_user_action_payload(payload)
    resolved_user_id = _resolve_user_id(current_user, wallet_address)
    try:
        await user_actions_protocol.execute_user_action(user_action, resolved_user_id)
    except RuntimeError as error:
        if str(error) == "Scheduler is not initialized":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler not initialized",
            ) from error
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
