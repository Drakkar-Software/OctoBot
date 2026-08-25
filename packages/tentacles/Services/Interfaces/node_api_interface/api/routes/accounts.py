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

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

import octobot_node.protocol.accounts_history as accounts_history_module

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

router = APIRouter(tags=["accounts"])


@router.get("/aggregated/historical-values")
async def get_aggregated_account_historical_values(
    current_user: CurrentUser,
    is_simulated: bool = Query(...),
    wallet_address: typing.Optional[str] = Query(default=None),
) -> JSONResponse:
    """Compute aggregated portfolio historical values for all matching accounts."""
    ensure_debug_routes_enabled()
    ensure_scheduler_initialized()
    resolved_user_id = resolve_user_id(current_user, wallet_address)
    history_state = (
        await accounts_history_module.compute_aggregated_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            resolved_user_id,
            is_simulated=is_simulated,
        )
    )
    return JSONResponse(content=json.loads(history_state.to_json()))


@router.get("/{account_id}/historical-values")
async def get_account_historical_values(
    account_id: str,
    current_user: CurrentUser,
    wallet_address: typing.Optional[str] = Query(default=None),
) -> JSONResponse:
    """Compute portfolio historical values on-the-fly for an account."""
    ensure_debug_routes_enabled()
    ensure_scheduler_initialized()
    resolved_user_id = resolve_user_id(current_user, wallet_address)
    history_state = (
        await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            resolved_user_id,
            account_id,
        )
    )
    return JSONResponse(content=json.loads(history_state.to_json()))
