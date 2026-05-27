#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime

import mock
import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module

import octobot_node.scheduler.user_actions.user_actions_executor.util.action_details_factory as action_details_factory_module

from ..account import account_executor_test_utils


_WALLET_ADDRESS = account_executor_test_utils.WALLET_ADDRESS
_ACCOUNT_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def _live_exchange_account() -> protocol_models.Account:
    return protocol_models.Account(
        id="acc-1",
        name="Test exchange account",
        is_simulated=False,
        created_at=_ACCOUNT_TIMESTAMP,
        updated_at=_ACCOUNT_TIMESTAMP,
        authentication_id="wallet-auth-id",
        assets=account_executor_test_utils.assets_payload(),
        specifics=protocol_models.AccountSpecifics(
            actual_instance=account_executor_test_utils.exchange_account_payload(),
        ),
    )


def _authentication(
    *,
    api_passphrase: str | None = None,
) -> protocol_models.AccountAuthentication:
    return protocol_models.AccountAuthentication(
        id="wallet-auth-id",
        api_key="plain-key",
        api_secret="plain-secret",
        api_passphrase=api_passphrase,
    )


def _auth_details_from_result(result: dict) -> exchange_data_module.ExchangeAuthDetails:
    exchange_account_details_dict = result["exchange_account_details"]
    return exchange_data_module.ExchangeAuthDetails.from_dict(
        exchange_account_details_dict["auth_details"],
    )


class TestExchangeProtocolAccountToApplyConfigurationDictEncryptsCredentials:
    def test_encrypts_api_key_and_api_secret(self):
        account = _live_exchange_account()
        authentication = _authentication()
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        with (
            mock.patch.object(
                action_details_factory_module.exchange_account_resolver,
                "get_exchange_config",
                return_value=account_executor_test_utils.exchange_config_payload(),
            ),
            mock.patch.object(
                action_details_factory_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
            mock.patch.object(
                action_details_factory_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
        ):
            result = action_details_factory_module.exchange_protocol_account_to_apply_configuration_dict(
                account,
                wallet_address=_WALLET_ADDRESS,
            )
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        assert encrypt_mock.call_count == 2
        auth_details = _auth_details_from_result(result)
        assert auth_details.api_key == "enc:plain-key"
        assert auth_details.api_secret == "enc:plain-secret"
        assert auth_details.api_password == ""

    def test_encrypts_passphrase_when_present(self):
        account = _live_exchange_account()
        authentication = _authentication(api_passphrase="plain-pass")
        encrypt_mock = mock.Mock(
            side_effect=lambda plain_text: ("enc:" + plain_text).encode(),
        )
        with (
            mock.patch.object(
                action_details_factory_module.exchange_account_resolver,
                "get_exchange_config",
                return_value=account_executor_test_utils.exchange_config_payload(),
            ),
            mock.patch.object(
                action_details_factory_module.account_authentication_resolver,
                "get_exchange_authentication",
                return_value=authentication,
            ),
            mock.patch.object(
                action_details_factory_module.fields_utils,
                "encrypt",
                encrypt_mock,
            ),
        ):
            result = action_details_factory_module.exchange_protocol_account_to_apply_configuration_dict(
                account,
                wallet_address=_WALLET_ADDRESS,
            )
        encrypt_mock.assert_any_call("plain-key")
        encrypt_mock.assert_any_call("plain-secret")
        encrypt_mock.assert_any_call("plain-pass")
        assert encrypt_mock.call_count == 3
        auth_details = _auth_details_from_result(result)
        assert auth_details.api_password == "enc:plain-pass"
