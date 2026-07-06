#  Drakkar-Software OctoBot-Sync
#  Copyright (c) Drakkar-Software, All rights reserved.
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
import pytest

import octobot.community.authentication as community_authentication
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers.validation.exchange_account_identity as exchange_account_identity_module
import octobot_sync.sync.collection_providers.user_account_provider as account_provider_module
import octobot_protocol.models as protocol_models

_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_PRIVATE_KEY = "private-key"
_DEFAULT_EXCHANGE_CONFIG_ID = "cfg-1"


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet_by_user_id.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


def _make_provider(tmp_path):
    return account_provider_module.AccountProvider(base_folder=str(tmp_path))


def _fixture_time() -> datetime.datetime:
    return datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)


def _sample_exchange_config(
    *,
    config_id: str = _DEFAULT_EXCHANGE_CONFIG_ID,
    exchange: str = "binanceus",
    url: str | None = None,
    sandboxed: bool = False,
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=config_id,
        name="binance-main",
        exchange=exchange,
        sandboxed=sandboxed,
        url=url,
    )


def _exchange_account_specifics(
    *,
    remote_account_id: str,
    exchange_config_ids: list[str] | None = None,
) -> protocol_models.AccountSpecifics:
    return protocol_models.AccountSpecifics(
        actual_instance=protocol_models.ExchangeAccount(
            account_type=protocol_models.AccountType.EXCHANGE,
            remote_account_id=remote_account_id,
            exchange_config_ids=exchange_config_ids or [_DEFAULT_EXCHANGE_CONFIG_ID],
        ),
    )


def _live_exchange_account(
    *,
    account_id: str,
    remote_account_id: str,
    is_simulated: bool = False,
    exchange_config_ids: list[str] | None = None,
    name: str = "Test account",
) -> protocol_models.Account:
    fixture_time = _fixture_time()
    return protocol_models.Account(
        id=account_id,
        name=name,
        is_simulated=is_simulated,
        created_at=fixture_time,
        updated_at=fixture_time,
        specifics=_exchange_account_specifics(
            remote_account_id=remote_account_id,
            exchange_config_ids=exchange_config_ids,
        ),
    )


class TestNormalizeExchangeUrl:
    def test_none_stays_none(self):
        assert exchange_account_identity_module._normalize_exchange_url(None) is None

    def test_empty_string_becomes_none(self):
        assert exchange_account_identity_module._normalize_exchange_url("") is None

    def test_non_empty_url_preserved(self):
        assert exchange_account_identity_module._normalize_exchange_url("https://api.binance.com") == (
            "https://api.binance.com"
        )


class TestResolveExchangeAccountIdentity:
    def test_returns_none_for_simulated_account(self):
        account = _live_exchange_account(
            account_id="acc-1",
            remote_account_id="remote-1",
            is_simulated=True,
        )
        exchange_configs_by_id = {_DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config()}
        assert exchange_account_identity_module._resolve_exchange_account_identity(
            account,
            exchange_configs_by_id,
        ) is None

    def test_returns_none_for_non_exchange_specifics(self):
        fixture_time = _fixture_time()
        account = protocol_models.Account(
            id="acc-1",
            name="Blockchain",
            is_simulated=False,
            created_at=fixture_time,
            updated_at=fixture_time,
            specifics=protocol_models.AccountSpecifics(
                actual_instance=protocol_models.BlockchainAccount(
                    account_type=protocol_models.AccountType.BLOCKCHAIN,
                    blockchain="ethereum",
                    public_key="0x1234567890123456789012345678901234567890",
                ),
            ),
        )
        exchange_configs_by_id = {_DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config()}
        assert exchange_account_identity_module._resolve_exchange_account_identity(
            account,
            exchange_configs_by_id,
        ) is None

    def test_resolves_identity_from_exchange_config(self):
        account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        exchange_configs_by_id = {
            _DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config(
                exchange="binanceus",
                url="https://api.binance.us",
                sandboxed=True,
            ),
        }
        identity = exchange_account_identity_module._resolve_exchange_account_identity(
            account,
            exchange_configs_by_id,
        )
        assert identity == exchange_account_identity_module.ExchangeAccountIdentity(
            remote_account_id="remote-1",
            exchange="binanceus",
            url="https://api.binance.us",
            sandboxed=True,
        )

    def test_falls_back_to_account_id_when_remote_account_id_empty(self):
        account = _live_exchange_account(account_id="acc-1", remote_account_id="")
        exchange_configs_by_id = {_DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config()}
        identity = exchange_account_identity_module._resolve_exchange_account_identity(
            account,
            exchange_configs_by_id,
        )
        assert identity is not None
        assert identity.remote_account_id == "acc-1"


class TestFindConflictingAccount:
    def test_finds_matching_account(self):
        first_account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        second_account = _live_exchange_account(account_id="acc-2", remote_account_id="remote-1")
        exchange_configs_by_id = {_DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config()}
        candidate_identity = exchange_account_identity_module._resolve_exchange_account_identity(
            second_account,
            exchange_configs_by_id,
        )
        assert candidate_identity is not None
        conflict = exchange_account_identity_module._find_conflicting_account(
            [first_account],
            exchange_configs_by_id,
            candidate_identity,
        )
        assert conflict is first_account

    def test_excludes_account_id_when_requested(self):
        account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        exchange_configs_by_id = {_DEFAULT_EXCHANGE_CONFIG_ID: _sample_exchange_config()}
        candidate_identity = exchange_account_identity_module._resolve_exchange_account_identity(
            account,
            exchange_configs_by_id,
        )
        assert candidate_identity is not None
        conflict = exchange_account_identity_module._find_conflicting_account(
            [account],
            exchange_configs_by_id,
            candidate_identity,
            exclude_account_id="acc-1",
        )
        assert conflict is None


class TestAssertUniqueExchangeAccountIdentity:
    def test_no_op_for_simulated_account(self):
        account = _live_exchange_account(
            account_id="acc-1",
            remote_account_id="remote-1",
            is_simulated=True,
        )
        exchange_account_identity_module.assert_unique_exchange_account_identity(
            _TEST_ADDRESS,
            account,
            [],
            [_sample_exchange_config()],
        )

    def test_no_op_for_non_exchange_specifics(self):
        fixture_time = _fixture_time()
        account = protocol_models.Account(
            id="acc-1",
            name="Blockchain",
            is_simulated=False,
            created_at=fixture_time,
            updated_at=fixture_time,
            specifics=protocol_models.AccountSpecifics(
                actual_instance=protocol_models.BlockchainAccount(
                    account_type=protocol_models.AccountType.BLOCKCHAIN,
                    blockchain="ethereum",
                    public_key="0x1234567890123456789012345678901234567890",
                ),
            ),
        )
        exchange_account_identity_module.assert_unique_exchange_account_identity(
            _TEST_ADDRESS,
            account,
            [],
            [_sample_exchange_config()],
        )

    def test_raises_when_identity_collides(self):
        first_account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        second_account = _live_exchange_account(account_id="acc-2", remote_account_id="remote-1")
        exchange_configs = [_sample_exchange_config()]
        with pytest.raises(collection_errors.DuplicateItemError) as raised:
            exchange_account_identity_module.assert_unique_exchange_account_identity(
                _TEST_ADDRESS,
                second_account,
                [first_account],
                exchange_configs,
            )
        assert _TEST_ADDRESS in str(raised.value)
        assert "acc-1" in str(raised.value)

    def test_passes_when_exclude_account_id_matches_self(self):
        account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        exchange_configs = [_sample_exchange_config()]
        exchange_account_identity_module.assert_unique_exchange_account_identity(
            _TEST_ADDRESS,
            account,
            [account],
            exchange_configs,
            exclude_account_id="acc-1",
        )


class TestAccountProviderCreateItemExchangeAccountIdentity:
    def _seed_exchange_config(self, provider, exchange_config: protocol_models.ExchangeConfig | None = None):
        config = exchange_config or _sample_exchange_config()
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, config)
        return config

    def test_duplicate_remote_identity_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        self._seed_exchange_config(provider)
        first_account = _live_exchange_account(account_id="acc-1", remote_account_id="remote-1")
        second_account = _live_exchange_account(account_id="acc-2", remote_account_id="remote-1")
        with _patch_wallet():
            provider.create_item(_TEST_ADDRESS, first_account)
        with pytest.raises(collection_errors.DuplicateItemError, match="remote-1"):
            with _patch_wallet():
                provider.create_item(_TEST_ADDRESS, second_account)

    def test_different_remote_id_allowed(self, tmp_path):
        provider = _make_provider(tmp_path)
        self._seed_exchange_config(provider)
        with _patch_wallet():
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(account_id="acc-1", remote_account_id="remote-1"),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(account_id="acc-2", remote_account_id="remote-2"),
            )
        assert len(provider.list_items(_TEST_ADDRESS)) == 2

    def test_different_url_allowed(self, tmp_path):
        provider = _make_provider(tmp_path)
        self._seed_exchange_config(provider, _sample_exchange_config(config_id="cfg-live", url=None))
        with _patch_wallet():
            provider.create_exchange_config(
                _TEST_ADDRESS,
                _sample_exchange_config(config_id="cfg-custom", url="https://custom.example"),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-1",
                    remote_account_id="remote-1",
                    exchange_config_ids=["cfg-live"],
                ),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-2",
                    remote_account_id="remote-1",
                    exchange_config_ids=["cfg-custom"],
                ),
            )
        assert len(provider.list_items(_TEST_ADDRESS)) == 2

    def test_sandboxed_differs_allowed(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_exchange_config(
                _TEST_ADDRESS,
                _sample_exchange_config(config_id="cfg-live", sandboxed=False),
            )
            provider.create_exchange_config(
                _TEST_ADDRESS,
                _sample_exchange_config(config_id="cfg-sandbox", sandboxed=True),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-1",
                    remote_account_id="remote-1",
                    exchange_config_ids=["cfg-live"],
                ),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-2",
                    remote_account_id="remote-1",
                    exchange_config_ids=["cfg-sandbox"],
                ),
            )
        assert len(provider.list_items(_TEST_ADDRESS)) == 2

    def test_simulated_accounts_skipped(self, tmp_path):
        provider = _make_provider(tmp_path)
        self._seed_exchange_config(provider)
        with _patch_wallet():
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-1",
                    remote_account_id="remote-1",
                    is_simulated=True,
                ),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-2",
                    remote_account_id="remote-1",
                    is_simulated=True,
                ),
            )
        assert len(provider.list_items(_TEST_ADDRESS)) == 2


class TestAccountProviderUpdateItemExchangeAccountIdentity:
    def test_edit_same_identity_allowed(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config())
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(account_id="acc-1", remote_account_id="remote-1"),
            )
            provider.update_item(
                _TEST_ADDRESS,
                _live_exchange_account(
                    account_id="acc-1",
                    remote_account_id="remote-1",
                    name="Renamed account",
                ),
            )
        updated = provider.get_item(_TEST_ADDRESS, "acc-1")
        assert updated.name == "Renamed account"

    def test_edit_to_conflicting_identity_raises(self, tmp_path):
        provider = _make_provider(tmp_path)
        with _patch_wallet():
            provider.create_exchange_config(_TEST_ADDRESS, _sample_exchange_config())
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(account_id="acc-1", remote_account_id="remote-1"),
            )
            provider.create_item(
                _TEST_ADDRESS,
                _live_exchange_account(account_id="acc-2", remote_account_id="remote-2"),
            )
        with pytest.raises(collection_errors.DuplicateItemError, match="remote-1"):
            with _patch_wallet():
                provider.update_item(
                    _TEST_ADDRESS,
                    _live_exchange_account(account_id="acc-2", remote_account_id="remote-1"),
                )
