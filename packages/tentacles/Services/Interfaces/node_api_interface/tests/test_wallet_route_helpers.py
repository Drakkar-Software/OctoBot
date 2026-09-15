#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import uuid

import mock
import pytest
from fastapi import HTTPException

import octobot_node.config
import octobot_node.models
import octobot_node.scheduler

try:
    from tentacles.Services.Interfaces.node_api_interface.api.wallet_route_helpers import (  # type: ignore[no-redef]
        ensure_debug_routes_enabled,
        ensure_scheduler_initialized,
        resolve_user_id,
        resolve_wallet_address,
    )
    import tentacles.Services.Interfaces.node_api_interface.api.wallet_route_helpers as wallet_route_helpers_module  # type: ignore[no-redef]
except ImportError:
    from api.wallet_route_helpers import (  # type: ignore[no-redef]
        ensure_debug_routes_enabled,
        ensure_scheduler_initialized,
        resolve_user_id,
        resolve_wallet_address,
    )
    import api.wallet_route_helpers as wallet_route_helpers_module  # type: ignore[no-redef]


def _user(email: str, is_superuser: bool = False) -> octobot_node.models.User:
    return octobot_node.models.User(
        id=uuid.uuid5(uuid.NAMESPACE_URL, email),
        email=email,
        is_active=True,
        is_superuser=is_superuser,
        full_name="Test User",
    )


class TestResolveWalletAddress:
    def test_returns_authenticated_wallet_when_query_param_missing(self):
        current_user = _user("0xabc")
        assert resolve_wallet_address(current_user, None) == "0xabc"

    def test_returns_matching_wallet_for_same_user(self):
        current_user = _user("0xAbC")
        assert resolve_wallet_address(current_user, "0xabc") == "0xabc"

    def test_allows_superuser_to_target_other_wallet(self):
        current_user = _user("0xowner", is_superuser=True)
        assert resolve_wallet_address(current_user, "0xother") == "0xother"

    def test_forbids_non_superuser_other_wallet(self):
        current_user = _user("0xowner", is_superuser=False)
        with pytest.raises(HTTPException) as error:
            resolve_wallet_address(current_user, "0xother")
        assert error.value.status_code == 403


class TestResolveUserId:
    @mock.patch.object(wallet_route_helpers_module, "evm_to_user_id", return_value="starfish-user")
    def test_maps_wallet_to_starfish_user_id(self, mock_evm_to_user_id):
        current_user = _user("0xabc")
        assert resolve_user_id(current_user, None) == "starfish-user"
        mock_evm_to_user_id.assert_called_once_with("0xabc")


class TestEnsureDebugRoutesEnabled:
    def test_raises_404_when_node_side_encryption_enabled(self):
        with mock.patch.object(
            type(octobot_node.config.settings),
            "is_node_side_encryption_enabled",
            new_callable=mock.PropertyMock,
            return_value=True,
        ):
            with pytest.raises(HTTPException) as error:
                ensure_debug_routes_enabled()
        assert error.value.status_code == 404


class TestEnsureSchedulerInitialized:
    def test_raises_503_when_scheduler_not_initialized(self):
        with mock.patch("octobot_node.scheduler.is_initialized", return_value=False):
            with pytest.raises(HTTPException) as error:
                ensure_scheduler_initialized()
        assert error.value.status_code == 503
