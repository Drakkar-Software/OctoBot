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

from fastapi import HTTPException, status

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler

try:
    from tentacles.Services.Interfaces.node_api_interface.api.user_id import evm_to_user_id  # type: ignore[no-redef]
except ImportError:
    from api.user_id import evm_to_user_id  # type: ignore[no-redef]


def resolve_wallet_address(
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


def resolve_user_id(
    current_user: octobot_node.models.User,
    wallet_address: typing.Optional[str],
) -> str:
    """Resolve EVM wallet address to the Starfish user_id used by the sync-core.

    The HTTP debug API accepts the EVM address for user-facing consistency, but all
    internal protocol and scheduler calls use the Starfish user_id.
    """
    evm_address = resolve_wallet_address(current_user, wallet_address)
    return evm_to_user_id(evm_address)


def ensure_debug_routes_enabled() -> None:
    if octobot_node.config.settings.is_node_side_encryption_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug routes are disabled when node-side encryption is enabled",
        )


def ensure_scheduler_initialized() -> None:
    if not octobot_node.scheduler.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler not initialized",
        )
