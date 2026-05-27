import datetime

import mock
import pytest

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors

import octobot_node.errors as node_errors
import octobot_node.scheduler.user_actions.user_actions_executor.util.account_authentication_resolver as account_authentication_resolver_module

from ..account import account_executor_test_utils

_WALLET_ADDRESS = account_executor_test_utils.WALLET_ADDRESS
_ACCOUNT_TIMESTAMP = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
_AUTHENTICATION_ID = "wallet-auth-id"


_UNSET = object()


def _exchange_account(
    *,
    account_id: str = "acc-1",
    authentication_id: str | None = _AUTHENTICATION_ID,
    is_simulated: bool = False,
    specifics: protocol_models.AccountSpecifics | None | object = _UNSET,
) -> protocol_models.Account:
    if specifics is _UNSET:
        resolved_specifics = protocol_models.AccountSpecifics(
            actual_instance=account_executor_test_utils.exchange_account_payload(),
        )
    else:
        resolved_specifics = specifics
    return protocol_models.Account(
        id=account_id,
        name="Test exchange account",
        is_simulated=is_simulated,
        created_at=_ACCOUNT_TIMESTAMP,
        updated_at=_ACCOUNT_TIMESTAMP,
        authentication_id=authentication_id,
        assets=account_executor_test_utils.assets_payload(),
        specifics=resolved_specifics,
    )


class TestGetExchangeAuthentication:
    def test_returns_none_for_simulated_account(self):
        account = _exchange_account(is_simulated=True)
        assert (
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )
            is None
        )

    def test_raises_when_specifics_missing(self):
        account = _exchange_account(specifics=None)
        with pytest.raises(
            node_errors.AccountAuthenticationNotFoundError,
            match="has no specifics for authentication lookup",
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_raises_when_specifics_instance_is_none(self):
        account = _exchange_account(
            specifics=protocol_models.AccountSpecifics.model_construct(actual_instance=None),
        )
        with pytest.raises(
            node_errors.AccountAuthenticationNotFoundError,
            match="has no specifics for authentication lookup",
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_raises_when_account_is_not_exchange_account(self):
        account = account_executor_test_utils.minimal_blockchain_account(account_id="acc-1")
        with pytest.raises(
            node_errors.AccountAuthenticationNotFoundError,
            match="is not an exchange account",
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_raises_when_authentication_id_missing(self):
        account = _exchange_account(authentication_id=None)
        with pytest.raises(
            node_errors.AccountAuthenticationNotFoundError,
            match="has no authentication_id for authentication lookup",
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_returns_authentication_from_provider_using_authentication_id(self):
        account = _exchange_account(
            account_id="acc-1",
            authentication_id=_AUTHENTICATION_ID,
        )
        sample_authentication = account_executor_test_utils.authentication_payload(
            auth_id=_AUTHENTICATION_ID,
        )
        provider_mock = mock.Mock()
        provider_mock.get_item = mock.Mock(return_value=sample_authentication)
        with mock.patch.object(
            account_authentication_resolver_module.collection_providers.AccountAuthenticationProvider,
            "instance",
            return_value=provider_mock,
        ):
            authentication = account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )
        provider_mock.get_item.assert_called_once_with(_WALLET_ADDRESS, _AUTHENTICATION_ID)
        assert authentication == sample_authentication

    def test_raises_when_provider_item_not_found(self):
        account = _exchange_account()
        provider_mock = mock.Mock()
        provider_mock.get_item = mock.Mock(
            side_effect=collection_errors.ItemNotFoundError(_AUTHENTICATION_ID),
        )
        with (
            mock.patch.object(
                account_authentication_resolver_module.collection_providers.AccountAuthenticationProvider,
                "instance",
                return_value=provider_mock,
            ),
            pytest.raises(
                node_errors.AccountAuthenticationNotFoundError,
                match=f"Authentication {_AUTHENTICATION_ID!r} for account 'acc-1'",
            ),
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_raises_when_api_key_missing(self):
        account = _exchange_account()
        sample_authentication = protocol_models.AccountAuthentication(
            id=_AUTHENTICATION_ID,
            api_key=None,
            api_secret="secret",
        )
        provider_mock = mock.Mock()
        provider_mock.get_item = mock.Mock(return_value=sample_authentication)
        with (
            mock.patch.object(
                account_authentication_resolver_module.collection_providers.AccountAuthenticationProvider,
                "instance",
                return_value=provider_mock,
            ),
            pytest.raises(
                node_errors.AccountAuthenticationNotFoundError,
                match="is missing api_key or api_secret",
            ),
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )

    def test_raises_when_api_secret_missing(self):
        account = _exchange_account()
        sample_authentication = protocol_models.AccountAuthentication(
            id=_AUTHENTICATION_ID,
            api_key="key",
            api_secret=None,
        )
        provider_mock = mock.Mock()
        provider_mock.get_item = mock.Mock(return_value=sample_authentication)
        with (
            mock.patch.object(
                account_authentication_resolver_module.collection_providers.AccountAuthenticationProvider,
                "instance",
                return_value=provider_mock,
            ),
            pytest.raises(
                node_errors.AccountAuthenticationNotFoundError,
                match="is missing api_key or api_secret",
            ),
        ):
            account_authentication_resolver_module.get_exchange_authentication(
                _WALLET_ADDRESS,
                account,
            )
