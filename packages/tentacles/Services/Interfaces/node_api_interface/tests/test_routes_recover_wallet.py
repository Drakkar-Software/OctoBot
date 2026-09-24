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

import octobot.community.wallet_backend as wallet_backend

from tentacles.Services.Interfaces.node_api_interface.api.rate_limits.recover_passphrase import (
    get_recover_passphrase_rate_limiter,
)

from .conftest import ADMIN_ADDRESS

_TEST_MNEMONIC = "test test test test test test test test test test test junk"
_RECOVER_URL = "/api/v1/setup/wallet/recover-from-seed"


def _recover_body(**overrides):
    body = {
        "address": ADMIN_ADDRESS,
        "new_passphrase": "new-passphrase99",
        "seed": _TEST_MNEMONIC,
    }
    body.update(overrides)
    return body


def test_recover_wallet_success(client):
    auth = mock.MagicMock()
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        get_recover_passphrase_rate_limiter().reset_all()
        resp = client.post(_RECOVER_URL, json=_recover_body())
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    auth.recover_passphrase_from_ownership_proof.assert_called_once()


def test_recover_wallet_mismatch_returns_401(client):
    auth = mock.MagicMock()
    auth.recover_passphrase_from_ownership_proof.side_effect = (
        wallet_backend.WalletProofMismatchError("mismatch")
    )
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        get_recover_passphrase_rate_limiter().reset_all()
        resp = client.post(_RECOVER_URL, json=_recover_body())
    assert resp.status_code == 401


def test_recover_wallet_read_only_returns_503(client):
    auth = mock.MagicMock()
    auth.recover_passphrase_from_ownership_proof.side_effect = (
        wallet_backend.WalletStorageReadOnlyError("read-only")
    )
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        get_recover_passphrase_rate_limiter().reset_all()
        resp = client.post(_RECOVER_URL, json=_recover_body())
    assert resp.status_code == 503
    assert "read-only" in resp.json()["detail"].lower()


def test_recover_wallet_rate_limited_after_ip_failures(client):
    auth = mock.MagicMock()
    auth.recover_passphrase_from_ownership_proof.side_effect = (
        wallet_backend.WalletProofMismatchError("mismatch")
    )
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        limiter = get_recover_passphrase_rate_limiter()
        limiter.reset_all()
        for _ in range(5):
            resp = client.post(_RECOVER_URL, json=_recover_body())
            assert resp.status_code == 401
        resp = client.post(_RECOVER_URL, json=_recover_body())
    assert resp.status_code == 429
