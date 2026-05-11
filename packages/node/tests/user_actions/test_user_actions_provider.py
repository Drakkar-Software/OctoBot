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
import time

import pytest

import octobot_protocol.models as protocol_models

import octobot_node.errors as node_errors
import octobot_node.user_actions.user_actions_provider as user_actions_provider_module

_WALLET_A = "0xwallet_a_test_provider"
_WALLET_B = "0xwallet_b_test_provider"


def _provider(**kwargs):
    return user_actions_provider_module.UserActionsProvider.instance(**kwargs)


def _minimal_user_action(*, user_action_id: str) -> protocol_models.UserAction:
    return protocol_models.UserAction(id=user_action_id, configuration=None)


class TestCreateUserAction:
    def test_sets_timestamps_and_returns_detached_copy(self):
        provider = _provider(ttl_seconds=3600.0)
        incoming = _minimal_user_action(user_action_id="ua-1")
        created = provider.create_user_action(_WALLET_A, incoming)
        assert created is not incoming
        assert created.id == "ua-1"
        assert created.created_at is not None
        assert created.updated_at is not None
        assert created.created_at == created.updated_at

    def test_duplicate_id_raises(self):
        provider = _provider(ttl_seconds=3600.0)
        provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-dup"))
        with pytest.raises(node_errors.DuplicateUserActionError, match="ua-dup"):
            provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-dup"))


class TestGetUserAction:
    def test_returns_copy_after_create(self):
        provider = _provider(ttl_seconds=3600.0)
        provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-get"))
        fetched = provider.get_user_action(_WALLET_A, "ua-get")
        again = provider.get_user_action(_WALLET_A, "ua-get")
        assert fetched.id == again.id
        assert fetched is not again

    def test_missing_raises(self):
        provider = _provider(ttl_seconds=3600.0)
        with pytest.raises(node_errors.UserActionNotFoundError, match="ua-missing"):
            provider.get_user_action(_WALLET_A, "ua-missing")


class TestListUserActions:
    def test_empty_initially(self):
        provider = _provider(ttl_seconds=3600.0)
        assert provider.list_user_actions(_WALLET_A) == []

    def test_sorted_by_created_at_then_id(self):
        provider = _provider(ttl_seconds=3600.0)
        early = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        later = datetime.datetime(2025, 1, 1, tzinfo=datetime.UTC)
        provider.create_user_action(
            _WALLET_A,
            protocol_models.UserAction(
                id="ua-b",
                configuration=None,
                created_at=later,
                updated_at=later,
            ),
        )
        provider.create_user_action(
            _WALLET_A,
            protocol_models.UserAction(
                id="ua-a",
                configuration=None,
                created_at=early,
                updated_at=early,
            ),
        )
        identifiers = [entry.id for entry in provider.list_user_actions(_WALLET_A)]
        assert identifiers == ["ua-a", "ua-b"]


class TestUpdateUserAction:
    def test_bumps_updated_at_and_preserves_created_at_when_omitted(self):
        provider = _provider(ttl_seconds=3600.0)
        created_at = datetime.datetime(2020, 6, 1, 12, 0, 0, tzinfo=datetime.UTC)
        provider.create_user_action(
            _WALLET_A,
            protocol_models.UserAction(
                id="ua-upd",
                configuration=None,
                created_at=created_at,
                updated_at=created_at,
            ),
        )
        time.sleep(0.01)
        updated = provider.update_user_action(
            _WALLET_A,
            protocol_models.UserAction(
                id="ua-upd",
                status=protocol_models.UserActionStatus.COMPLETED,
                configuration=None,
                created_at=None,
                updated_at=None,
            ),
        )
        assert updated.created_at == created_at
        assert updated.updated_at is not None
        assert updated.updated_at > created_at
        assert updated.status == protocol_models.UserActionStatus.COMPLETED

    def test_missing_raises(self):
        provider = _provider(ttl_seconds=3600.0)
        with pytest.raises(node_errors.UserActionNotFoundError, match="ua-none"):
            provider.update_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-none"))


class TestDeleteUserAction:
    def test_removes_entry(self):
        provider = _provider(ttl_seconds=3600.0)
        provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-del"))
        provider.delete_user_action(_WALLET_A, "ua-del")
        with pytest.raises(node_errors.UserActionNotFoundError):
            provider.get_user_action(_WALLET_A, "ua-del")

    def test_missing_raises(self):
        provider = _provider(ttl_seconds=3600.0)
        with pytest.raises(node_errors.UserActionNotFoundError, match="ua-gone"):
            provider.delete_user_action(_WALLET_A, "ua-gone")


class TestTtlEviction:
    def test_expired_entry_not_retrievable(self):
        provider = _provider(ttl_seconds=0.05, maxsize=128)
        provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id="ua-ttl"))
        time.sleep(0.15)
        with pytest.raises(node_errors.UserActionNotFoundError, match="ua-ttl"):
            provider.get_user_action(_WALLET_A, "ua-ttl")
        assert provider.list_user_actions(_WALLET_A) == []


class TestSameUserActionIdAcrossWallets:
    def test_same_id_allowed_per_wallet_isolation(self):
        provider = _provider(ttl_seconds=3600.0)
        shared_id = "ua-shared-across-wallets"
        provider.create_user_action(_WALLET_A, _minimal_user_action(user_action_id=shared_id))
        provider.create_user_action(_WALLET_B, _minimal_user_action(user_action_id=shared_id))
        action_a = provider.get_user_action(_WALLET_A, shared_id)
        action_b = provider.get_user_action(_WALLET_B, shared_id)
        assert action_a.id == action_b.id == shared_id
        assert action_a is not action_b
        assert len(provider.list_user_actions(_WALLET_A)) == 1
        assert len(provider.list_user_actions(_WALLET_B)) == 1
