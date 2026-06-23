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

import mock


# A real (test-only) secp256k1 private key so eth_account can actually sign.
_TEST_PRIVATE_KEY = "0x" + "11" * 32


def _patched_auth_with_wallet():
    auth = mock.Mock()
    auth.get_wallet.return_value = mock.Mock(private_key=_TEST_PRIVATE_KEY)
    return mock.patch(
        "octobot.community.authentication.CommunityAuthentication.instance",
        return_value=auth,
    )


# GET /config/octochat-identity returns a deterministic wallet signature, auth-gated like the rest
class TestOctoChatIdentity:
    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.get("/api/v1/config/octochat-identity")
        assert response.status_code == 401

    def test_returns_deterministic_evm_signature(self, admin_client):
        with _patched_auth_with_wallet():
            first = admin_client.get("/api/v1/config/octochat-identity")
            second = admin_client.get("/api/v1/config/octochat-identity")
        assert first.status_code == 200
        body = first.json()
        # checksummed EVM address recovered from the signer key
        assert body["address"].startswith("0x")
        signature = body["signature"].removeprefix("0x")
        assert len(signature) == 130  # 65-byte r‖s‖v
        # deterministic (RFC 6979) — same wallet always yields the same identity
        assert second.json()["signature"] == body["signature"]


class TestOctoChatConfig:
    def test_without_auth_returns_401(self, client, mock_auth):
        response = client.get("/api/v1/config/octochat")
        assert response.status_code == 401
