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

from .conftest import (
    ADMIN_ADDRESS,
    ADMIN_PASSPHRASE,
    TENANT_ADDRESS,
    TENANT_PASSPHRASE,
)

NEW_WALLET_ADDRESS = "0xnew0000000000000000000000000000000001"


def test_list_wallets_unauthenticated(client, mock_auth):
    resp = client.get("/api/v1/wallets/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Admin flags must not be revealed without credentials
    for w in data:
        assert w["is_admin"] is False


def test_list_wallets_authenticated_reveals_admin_flags(client, mock_auth):
    resp = client.get("/api/v1/wallets/", auth=(ADMIN_ADDRESS, ADMIN_PASSPHRASE))
    assert resp.status_code == 200
    data = resp.json()
    admin_entry = next(w for w in data if w["address"] == ADMIN_ADDRESS)
    assert admin_entry["is_admin"] is True


def test_list_wallets_any_verified_user_sees_admin_flags(client, mock_auth):
    # Any valid credential (not just admin) reveals is_admin flags
    resp = client.get("/api/v1/wallets/", auth=(TENANT_ADDRESS, TENANT_PASSPHRASE))
    assert resp.status_code == 200
    data = resp.json()
    admin_entry = next(w for w in data if w["address"] == ADMIN_ADDRESS)
    assert admin_entry["is_admin"] is True


def test_list_wallets_bad_credentials_hides_admin_flags(client, mock_auth):
    resp = client.get("/api/v1/wallets/", auth=(ADMIN_ADDRESS, "wrongpass"))
    assert resp.status_code == 200
    for w in resp.json():
        assert w["is_admin"] is False


def test_list_wallets_unknown_address_hides_admin_flags(client, mock_auth):
    """Credentials for an address not in the wallet list must not reveal names/is_admin."""
    resp = client.get("/api/v1/wallets/", auth=("0xunknown000000000000000000000000000001", "anypass"))
    assert resp.status_code == 200
    for w in resp.json():
        assert w["is_admin"] is False
        assert w["name"] is None


def test_list_wallets_no_auth_service(client):
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=None,
    ):
        resp = client.get("/api/v1/wallets/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_wallet_as_admin(admin_client, mock_auth):
    mock_auth.create_wallet.return_value = mock.MagicMock(address=NEW_WALLET_ADDRESS)
    resp = admin_client.post("/api/v1/wallets/", json={"passphrase": "newpass123", "name": "Bob"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"] == NEW_WALLET_ADDRESS
    assert data["name"] == "Bob"
    assert data["is_admin"] is False
    mock_auth.create_wallet.assert_called_once_with(
        name="Bob", passphrase="newpass123", is_admin=False
    )


def test_create_wallet_as_tenant(tenant_client, mock_auth):
    resp = tenant_client.post("/api/v1/wallets/", json={"passphrase": "newpass123"})
    assert resp.status_code == 403


def test_create_wallet_with_private_key(admin_client, mock_auth):
    pk = "a" * 64
    mock_auth.import_wallet.return_value = mock.MagicMock(address=NEW_WALLET_ADDRESS)
    resp = admin_client.post(
        "/api/v1/wallets/",
        json={"passphrase": "newpass123", "private_key": pk, "name": "Imported"},
    )
    assert resp.status_code == 200
    mock_auth.import_wallet.assert_called_once_with(
        private_key=pk, passphrase="newpass123", name="Imported", is_admin=False
    )


def test_create_wallet_duplicate_raises_422(admin_client, mock_auth):
    mock_auth.create_wallet.side_effect = wallet_backend.WalletAlreadyExistsError("Wallet already exists")
    resp = admin_client.post("/api/v1/wallets/", json={"passphrase": "newpass123"})
    assert resp.status_code == 422


def test_create_wallet_service_unavailable(admin_client):
    with mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=None,
    ):
        resp = admin_client.post("/api/v1/wallets/", json={"passphrase": "newpass123"})
    assert resp.status_code == 503


def test_rename_wallet_as_admin(admin_client, mock_auth):
    mock_auth.rename_wallet.return_value = None
    mock_auth.is_admin_wallet.side_effect = lambda addr: addr == ADMIN_ADDRESS
    resp = admin_client.patch(
        f"/api/v1/wallets/{TENANT_ADDRESS}", json={"name": "Renamed"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Renamed"
    mock_auth.rename_wallet.assert_called_once_with(TENANT_ADDRESS, "Renamed")


def test_rename_wallet_as_tenant(tenant_client, mock_auth):
    resp = tenant_client.patch(f"/api/v1/wallets/{TENANT_ADDRESS}", json={"name": "X"})
    assert resp.status_code == 403


def test_rename_wallet_not_found(admin_client, mock_auth):
    mock_auth.rename_wallet.side_effect = wallet_backend.WalletNotFoundError("Wallet 0xunknown not found")
    resp = admin_client.patch("/api/v1/wallets/0xunknown", json={"name": "X"})
    assert resp.status_code == 404


def test_delete_wallet_as_admin(admin_client, mock_auth):
    mock_auth.remove_wallet.return_value = None
    resp = admin_client.delete(f"/api/v1/wallets/{TENANT_ADDRESS}")
    assert resp.status_code == 200
    assert resp.json()["address"] == TENANT_ADDRESS
    mock_auth.remove_wallet.assert_called_once_with(TENANT_ADDRESS)


def test_delete_wallet_as_tenant(tenant_client, mock_auth):
    resp = tenant_client.delete(f"/api/v1/wallets/{ADMIN_ADDRESS}")
    assert resp.status_code == 403


def test_delete_wallet_not_found(admin_client, mock_auth):
    mock_auth.remove_wallet.side_effect = wallet_backend.WalletNotFoundError("not found")
    resp = admin_client.delete("/api/v1/wallets/0xunknown")
    assert resp.status_code == 404


def test_delete_admin_wallet_raises_400(admin_client, mock_auth):
    mock_auth.remove_wallet.side_effect = wallet_backend.CannotRemoveAdminWalletError("Cannot remove the admin wallet")
    resp = admin_client.delete(f"/api/v1/wallets/{ADMIN_ADDRESS}")
    assert resp.status_code == 400


def test_delete_last_wallet_raises_400(admin_client, mock_auth):
    mock_auth.remove_wallet.side_effect = wallet_backend.CannotRemoveLastWalletError("Cannot remove the last wallet")
    resp = admin_client.delete(f"/api/v1/wallets/{ADMIN_ADDRESS}")
    assert resp.status_code == 400
