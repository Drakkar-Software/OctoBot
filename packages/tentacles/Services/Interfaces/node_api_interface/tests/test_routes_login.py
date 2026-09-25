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

import base64

from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.login import (
    LOGIN_RATE_LIMITED_DETAIL,
    get_login_rate_limiter,
)

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE

_LOGIN_TEST_URL = "/api/v1/login/test"


def _auth_header(address: str, passphrase: str) -> dict:
    token = base64.b64encode(f"{address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_login_success(client, mock_auth):
    get_login_rate_limiter().reset_all()
    resp = client.get(
        _LOGIN_TEST_URL,
        headers=_auth_header(ADMIN_ADDRESS, ADMIN_PASSPHRASE),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == ADMIN_ADDRESS


def test_login_rate_limited_after_ten_failures(client, mock_auth):
    limiter = get_login_rate_limiter()
    limiter.reset_all()
    wrong_headers = _auth_header(ADMIN_ADDRESS, "wrong-passphrase")
    for _ in range(10):
        resp = client.get(_LOGIN_TEST_URL, headers=wrong_headers)
        assert resp.status_code == 401
    resp = client.get(_LOGIN_TEST_URL, headers=wrong_headers)
    assert resp.status_code == 429
    assert resp.json()["detail"] == LOGIN_RATE_LIMITED_DETAIL


def test_login_success_resets_rate_limit(client, mock_auth):
    limiter = get_login_rate_limiter()
    limiter.reset_all()
    wrong_headers = _auth_header(ADMIN_ADDRESS, "wrong-passphrase")
    for _ in range(9):
        resp = client.get(_LOGIN_TEST_URL, headers=wrong_headers)
        assert resp.status_code == 401
    ok_resp = client.get(
        _LOGIN_TEST_URL,
        headers=_auth_header(ADMIN_ADDRESS, ADMIN_PASSPHRASE),
    )
    assert ok_resp.status_code == 200
    resp = client.get(_LOGIN_TEST_URL, headers=wrong_headers)
    assert resp.status_code == 401
