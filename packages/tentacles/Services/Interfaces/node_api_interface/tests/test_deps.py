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

from unittest import mock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from api.deps import get_current_user
from .conftest import (
    ADMIN_ADDRESS,
    ADMIN_PASSPHRASE,
    TENANT_ADDRESS,
    TENANT_PASSPHRASE,
)


def test_not_configured_auth_none():
    """auth is None → 503."""
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        assert exc_info.value.status_code == 503


def test_not_configured_no_wallets():
    """Empty wallet list → 503 (node not set up)."""
    auth = mock.MagicMock()
    auth.list_wallets.return_value = []
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        assert exc_info.value.status_code == 503


def test_multiwallet_correct_admin(mock_auth):
    creds = HTTPBasicCredentials(username=ADMIN_ADDRESS, password=ADMIN_PASSPHRASE)
    user = get_current_user(creds)
    assert user.is_superuser is True
    assert user.email == ADMIN_ADDRESS
    assert user.full_name == "Admin"


def test_multiwallet_correct_tenant(mock_auth):
    creds = HTTPBasicCredentials(username=TENANT_ADDRESS, password=TENANT_PASSPHRASE)
    user = get_current_user(creds)
    assert user.is_superuser is False
    assert user.email == TENANT_ADDRESS
    assert user.full_name == "Alice"


def test_multiwallet_wrong_passphrase(mock_auth):
    creds = HTTPBasicCredentials(username=ADMIN_ADDRESS, password="wrong")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_multiwallet_missing_username(mock_auth):
    creds = HTTPBasicCredentials(username="", password=ADMIN_PASSPHRASE)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_multiwallet_missing_passphrase(mock_auth):
    creds = HTTPBasicCredentials(username=ADMIN_ADDRESS, password="")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_multiwallet_unknown_address(mock_auth):
    """Address not in wallet list → 401."""
    creds = HTTPBasicCredentials(username="0xunknown", password="anypass")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401


def test_multiwallet_address_case_insensitive(mock_auth):
    """Uppercase address input must still authenticate correctly."""
    creds = HTTPBasicCredentials(username=ADMIN_ADDRESS.upper(), password=ADMIN_PASSPHRASE)
    user = get_current_user(creds)
    assert user.email == ADMIN_ADDRESS  # stored lowercase
