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

import octobot_node.models
import octobot_node.protocol.debug as debug_protocol
import octobot_node.protocol.user_actions as user_actions_protocol
import octobot_node.scheduler
import octobot_protocol.models as protocol_models

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import CurrentUser  # type: ignore[no-redef]
    from tentacles.Services.Interfaces.node_api_interface.api.wallet_route_helpers import (  # type: ignore[no-redef]
        ensure_debug_routes_enabled,
        ensure_scheduler_initialized,
        resolve_user_id,
    )
except ImportError:
    from api.deps import CurrentUser  # type: ignore[no-redef]
    from api.wallet_route_helpers import (  # type: ignore[no-redef]
        ensure_debug_routes_enabled,
        ensure_scheduler_initialized,
        resolve_user_id,
    )

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


def _extract_automation_parent_id(
    user_action: protocol_models.UserAction,
) -> typing.Optional[str]:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        return None
    payload = wrapper.actual_instance
    if isinstance(payload, protocol_models.StopAutomationConfiguration):
        return payload.id
    if isinstance(payload, protocol_models.RestartAutomationConfiguration):
        return payload.id
    if isinstance(payload, protocol_models.SignalAutomationConfiguration):
        return payload.automation_id
    return None


def _is_restart_automation_user_action(
    user_action: protocol_models.UserAction,
) -> bool:
    wrapper = user_action.configuration
    if wrapper is None or wrapper.actual_instance is None:
        return False
    return isinstance(wrapper.actual_instance, protocol_models.RestartAutomationConfiguration)


async def _resolve_execution_user_id(
    current_user: octobot_node.models.User,
    wallet_address: typing.Optional[str],
    user_action: protocol_models.UserAction,
) -> str:
    """Pick the Starfish user_id passed to the scheduler for this user action.

    For stop/signal/restart, the executor resolves the active DBOS workflow using a
    wallet-scoped lookup. Admins may act on another wallet's automation without passing
    ``wallet_address``, but only after API-side authorization and owner resolution here.
    """
    # Explicit wallet override: admin-gated in resolve_wallet_address.
    if wallet_address is not None:
        return resolve_user_id(current_user, wallet_address)

    caller_user_id = resolve_user_id(current_user, None)
    parent_automation_id = _extract_automation_parent_id(user_action)
    if parent_automation_id is None:
        return caller_user_id

    scheduler = octobot_node.scheduler.SCHEDULER
    is_restart = _is_restart_automation_user_action(user_action)
    # Caller-owned automation: keep the authenticated wallet's user_id.
    active_workflow_ids = await scheduler.resolve_active_automation_workflow_ids_for_parent_id(
        caller_user_id,
        parent_automation_id,
    )
    if active_workflow_ids:
        return caller_user_id

    if is_restart:
        terminal_workflow = await scheduler.resolve_latest_terminal_automation_workflow_for_parent_id(
            caller_user_id,
            parent_automation_id,
        )
        if terminal_workflow is not None:
            return caller_user_id

    # Cross-wallet: only superusers may resolve the automation owner without wallet filter.
    if current_user.is_superuser:
        owner_user_id = await scheduler.resolve_automation_owner_user_id(parent_automation_id)
        if owner_user_id is None and is_restart:
            owner_user_id = await scheduler.resolve_terminal_automation_owner_user_id(
                parent_automation_id
            )
        if owner_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation not found",
            )
        return owner_user_id

    # Non-superuser and automation not under caller's wallet.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Automation not found",
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
    ensure_debug_routes_enabled()
    ensure_scheduler_initialized()
    resolved_user_id = resolve_user_id(current_user, wallet_address)
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
    ensure_debug_routes_enabled()
    ensure_scheduler_initialized()
    user_action = _parse_user_action_payload(payload)
    resolved_user_id = await _resolve_execution_user_id(current_user, wallet_address, user_action)
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
