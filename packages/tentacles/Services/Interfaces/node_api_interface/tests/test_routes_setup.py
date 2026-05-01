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

from .conftest import ADMIN_ADDRESS, ADMIN_PASSPHRASE

_INIT_BODY = {
    "passphrase": "strongpass123",
    "node_type": "standalone",
    "name": "Primary",
}


def test_setup_status_not_configured(client):
    auth = mock.MagicMock()
    auth.list_wallets.return_value = []
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        resp = client.get("/api/v1/setup/status")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False}


def test_setup_status_configured(client):
    auth = mock.MagicMock()
    auth.list_wallets.return_value = [{"address": ADMIN_ADDRESS, "is_admin": True}]
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        resp = client.get("/api/v1/setup/status")
    assert resp.status_code == 200
    assert resp.json() == {"configured": True}


def test_setup_init_success(client):
    auth = mock.MagicMock()
    auth.list_wallets.return_value = []
    auth.create_wallet.return_value = mock.MagicMock(address=ADMIN_ADDRESS)
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        with mock.patch("octobot_node.config.settings"):
            resp = client.post("/api/v1/setup/init", json=_INIT_BODY)
    assert resp.status_code == 200
    assert resp.json()["address"] == ADMIN_ADDRESS
    auth.create_wallet.assert_called_once_with(
        name="Primary", passphrase="strongpass123", is_admin=True
    )


def test_setup_init_with_private_key(client):
    pk = "a" * 64
    auth = mock.MagicMock()
    auth.list_wallets.return_value = []
    auth.import_wallet.return_value = mock.MagicMock(address=ADMIN_ADDRESS)
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        with mock.patch("octobot_node.config.settings"):
            resp = client.post(
                "/api/v1/setup/init",
                json={**_INIT_BODY, "private_key": pk},
            )
    assert resp.status_code == 200
    auth.import_wallet.assert_called_once_with(
        private_key=pk, passphrase="strongpass123", name="Primary", is_admin=True
    )


def test_setup_init_already_configured_returns_409(client):
    auth = mock.MagicMock()
    auth.list_wallets.return_value = [{"address": ADMIN_ADDRESS, "is_admin": True}]
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        resp = client.post("/api/v1/setup/init", json=_INIT_BODY)
    assert resp.status_code == 409


def test_setup_init_invalid_passphrase_returns_422(client):
    auth = mock.MagicMock()
    auth.list_wallets.return_value = []
    auth.create_wallet.side_effect = wallet_backend.WalletError("Passphrase must be at least 8 characters")
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    ):
        with mock.patch("octobot_node.config.settings"):
            resp = client.post(
                "/api/v1/setup/init",
                json={**_INIT_BODY, "passphrase": "short"},
            )
    assert resp.status_code == 422


def test_wallet_export_success(admin_client, mock_auth):
    mock_auth.decrypt_wallet_by_address.return_value = mock.MagicMock(
        address=ADMIN_ADDRESS,
        private_key="0xdeadbeef",
    )
    resp = admin_client.get(
        "/api/v1/setup/wallet/export",
        auth=(ADMIN_ADDRESS, ADMIN_PASSPHRASE),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"] == ADMIN_ADDRESS
    assert data["private_key"] == "0xdeadbeef"
