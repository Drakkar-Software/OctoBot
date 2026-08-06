#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.

import octobot_trading.exchanges.util.exchange_data as exchange_data_module


class TestExchangeAuthDetailsNonCredentialDict:
    """Checks :func:`octobot_trading.exchanges.util.exchange_data.ExchangeAuthDetails.non_credential_dict`."""

    def test_includes_only_non_credential_fields(self):
        auth_details = {
            "api_key": "secret-key",
            "api_secret": "secret-secret",
            "api_password": "secret-pass",
            "access_token": "secret-token",
            "encrypted": "secret-encrypted",
            "exchange_type": "spot",
            "sandboxed": True,
            "broker_enabled": False,
            "exchange_account_id": "acc-1",
            "exchange_credential_id": "cred-1",
        }
        non_credential_auth_details = exchange_data_module.ExchangeAuthDetails.non_credential_dict(
            auth_details,
        )
        assert set(non_credential_auth_details.keys()) == set(
            exchange_data_module._NON_CREDENTIAL_EXCHANGE_AUTH_DETAILS_FIELDS
        ) - {"incompatible_assets"}
        assert "api_key" not in non_credential_auth_details
        assert "api_secret" not in non_credential_auth_details
        assert "api_password" not in non_credential_auth_details
        assert "access_token" not in non_credential_auth_details
        assert "encrypted" not in non_credential_auth_details
        assert non_credential_auth_details["exchange_type"] == "spot"
        assert non_credential_auth_details["sandboxed"] is True
        assert non_credential_auth_details["broker_enabled"] is False
        assert non_credential_auth_details["exchange_account_id"] == "acc-1"
        assert non_credential_auth_details["exchange_credential_id"] == "cred-1"

    def test_copies_incompatible_assets_without_transformation(self):
        auth_details = {
            "api_key": "secret-key",
            "incompatible_assets": [
                {"symbol": "BTC/USDT", "updated_at": 123.0},
            ],
        }
        non_credential_auth_details = exchange_data_module.ExchangeAuthDetails.non_credential_dict(
            auth_details,
        )
        assert non_credential_auth_details["incompatible_assets"] == [
            {"symbol": "BTC/USDT", "updated_at": 123.0},
        ]
