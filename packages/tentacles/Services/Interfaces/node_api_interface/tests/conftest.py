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

import os
import sys
import typing
import uuid
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

import octobot.community.wallet_backend as wallet_backend
import octobot_node.config as _node_config
import tentacles.Services.Interfaces.node_api_interface as node_api_interface_module

# Allow direct imports from the package (api.* fallback path in route files)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import get_current_user
    from tentacles.Services.Interfaces.node_api_interface.api.main import build_api_router
except ImportError:
    from api.deps import get_current_user  # type: ignore[no-redef]
    from api.main import build_api_router  # type: ignore[no-redef]
import octobot_node.models

ADMIN_ADDRESS = "0xadmin000000000000000000000000000000000001"
TENANT_ADDRESS = "0xuser001000000000000000000000000000000001"
ADMIN_PASSPHRASE = "admin-pass-123"
TENANT_PASSPHRASE = "tenant-pass-456"

ADMIN_TASK_ID = "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1"
TENANT_TASK_ID = "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"

ADMIN_USER_ID = "admin-user-id-aabbcc112233"
TENANT_USER_ID = "tenant-user-id-ddeeff445566"

_ADMIN_PRIVATE_KEY = "admin-test-private-key"
_TENANT_PRIVATE_KEY = "tenant-test-private-key"


def make_admin_user() -> octobot_node.models.User:
    return octobot_node.models.User(
        id=uuid.uuid5(uuid.NAMESPACE_URL, ADMIN_ADDRESS),
        email=ADMIN_ADDRESS,
        is_active=True,
        is_superuser=True,
        full_name="Admin",
    )


def make_tenant_user() -> octobot_node.models.User:
    return octobot_node.models.User(
        id=uuid.uuid5(uuid.NAMESPACE_URL, TENANT_ADDRESS),
        email=TENANT_ADDRESS,
        is_active=True,
        is_superuser=False,
        full_name="Alice",
    )


@pytest.fixture()
def app() -> FastAPI:
    fastapi_app = node_api_interface_module.NodeApiInterface.create_app()
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return fastapi_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def unit_app():
    """Minimal app for unit tests that use dependency_overrides."""
    application = FastAPI()
    application.include_router(build_api_router(), prefix="/api/v1")
    _disabled_settings = mock.Mock(is_node_side_encryption_enabled=False)
    with mock.patch.object(_node_config, "settings", _disabled_settings):
        yield application


@pytest.fixture
def admin_client(unit_app):
    unit_app.dependency_overrides[get_current_user] = make_admin_user
    with TestClient(unit_app, raise_server_exceptions=False) as c:
        yield c
    unit_app.dependency_overrides.clear()


@pytest.fixture
def tenant_client(unit_app):
    unit_app.dependency_overrides[get_current_user] = make_tenant_user
    with TestClient(unit_app, raise_server_exceptions=False) as c:
        yield c
    unit_app.dependency_overrides.clear()


@pytest.fixture
def mock_auth():
    """Multi-wallet auth mock — two wallets (admin + tenant)."""
    _wallets = {
        ADMIN_ADDRESS: {"is_admin": True, "name": "Admin", "passphrase": ADMIN_PASSPHRASE},
        TENANT_ADDRESS: {"is_admin": False, "name": "Alice", "passphrase": TENANT_PASSPHRASE},
    }

    def _authenticate(addr, pw):
        info = _wallets.get(addr)
        if info is None:
            raise wallet_backend.WalletNotFoundError(f"Wallet {addr} not found")
        if pw != info["passphrase"]:
            raise wallet_backend.InvalidPassphraseError("Invalid passphrase")
        return wallet_backend.WalletInfo(address=addr, is_admin=info["is_admin"], name=info["name"])

    auth = mock.MagicMock()
    auth.list_wallets.return_value = [
        wallet_backend.WalletInfo(address=ADMIN_ADDRESS, name="Admin", is_admin=True),
        wallet_backend.WalletInfo(address=TENANT_ADDRESS, name="Alice", is_admin=False),
    ]
    auth.authenticate_wallet.side_effect = _authenticate
    auth.verify_wallet_passphrase.side_effect = lambda addr, pw: (
        (addr == ADMIN_ADDRESS and pw == ADMIN_PASSPHRASE)
        or (addr == TENANT_ADDRESS and pw == TENANT_PASSPHRASE)
    )
    auth.is_admin_wallet.side_effect = lambda addr: addr == ADMIN_ADDRESS
    auth.get_wallet_name.side_effect = lambda addr: "Admin" if addr == ADMIN_ADDRESS else "Alice"

    _admin_wallet = mock.Mock(private_key=_ADMIN_PRIVATE_KEY)
    _tenant_wallet = mock.Mock(private_key=_TENANT_PRIVATE_KEY)

    def _get_wallet_for_bot(addr):
        if addr.lower() == ADMIN_ADDRESS.lower():
            return _admin_wallet
        if addr.lower() == TENANT_ADDRESS.lower():
            return _tenant_wallet
        raise ValueError(f"Unknown wallet address: {addr}")

    auth.get_wallet.side_effect = _get_wallet_for_bot

    _pk_to_user_id = {_ADMIN_PRIVATE_KEY: ADMIN_USER_ID, _TENANT_PRIVATE_KEY: TENANT_USER_ID}

    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        with mock.patch("octobot_sync.server.derive_user_id", side_effect=_pk_to_user_id.get):
            yield auth


def assert_response_headers(
    response,
    expected_content_type: typing.Optional[str] = None,
    expected_content_length: typing.Optional[int] = None,
):
    headers = {header_key.lower(): header_value for header_key, header_value in response.headers.items()}
    if expected_content_type is not None:
        assert headers["content-type"] == expected_content_type, (
            f"Content-Type is {headers.get('content-type')}"
        )
    else:
        assert headers["content-type"] == "application/json", (
            f"Content-Type is {headers.get('content-type')}"
        )
    allow_origin = headers.get("access-control-allow-origin")
    if allow_origin is not None:
        assert allow_origin == "*", (
            f"Access-Control-Allow-Origin is {allow_origin}"
        )
    if expected_content_length is not None:
        assert int(headers["content-length"]) == expected_content_length, (
            f"Content-Length is {headers.get('content-length')}"
        )
    else:
        assert int(headers.get("content-length", 0)) > 0, (
            f"Content-Length is {headers.get('content-length')}"
        )
