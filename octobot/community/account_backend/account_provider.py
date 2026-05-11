#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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


import typing

import cachetools
import octobot_commons.singleton.singleton_class as singleton_class
import octobot_protocol.models as protocol_models

import octobot.community.authentication as community_authentication

import octobot.community.account_backend.errors as account_backend_errors
import octobot.community.account_backend.account_storage as account_storage


class AccountProvider(singleton_class.Singleton):
    """
    Singleton provider exposing CRUD operations on protocol Account models.

    Accounts are grouped per wallet address and persisted via AccountStorage.
    """

    def __init__(self, storage: typing.Optional[account_storage.AccountStorage] = None) -> None:
        self._storage = storage if storage is not None else account_storage.AccountStorage()
        # Cache keyed only by wallet address (AccountProvider is the only writer).
        self._cache: cachetools.TTLCache[str, list[protocol_models.Account]] = cachetools.TTLCache(
            maxsize=1024,
            ttl=12 * 60 * 60,
        )

    def _get_wallet_private_key(self, address: str) -> str:
        wallet = community_authentication.CommunityAuthentication.instance().get_wallet(address)
        return wallet.private_key

    def _get_cached_accounts(self, address: str) -> typing.Optional[list[protocol_models.Account]]:
        cached = self._cache.get(address)
        if cached is None:
            return None
        return list(cached)

    def _set_cached_accounts(self, address: str, accounts: list[protocol_models.Account]) -> None:
        self._cache[address] = list(accounts)

    def list_accounts(self, address: str) -> list[protocol_models.Account]:
        cached = self._get_cached_accounts(address)
        if cached is not None:
            return cached
        return self._refresh_accounts_cache(address)

    def _refresh_accounts_cache(self, address: str) -> list[protocol_models.Account]:
        wallet_private_key = self._get_wallet_private_key(address)
        raw_accounts = self._storage.load_accounts(address, wallet_private_key)
        accounts: list[protocol_models.Account] = []
        for raw in raw_accounts:
            account = protocol_models.Account.from_dict(raw)
            if account is not None:
                accounts.append(account)
        self._set_cached_accounts(address, accounts)
        return accounts

    def get_account(self, address: str, account_id: str) -> protocol_models.Account:
        for account in self.list_accounts(address):
            if account.id == account_id:
                return account
        raise account_backend_errors.AccountNotFoundError(
            f"Account {account_id} not found for address {address}"
        )

    def create_account(self, address: str, account: protocol_models.Account) -> protocol_models.Account:
        accounts = self._refresh_accounts_cache(address)
        if any(existing.id == account.id for existing in accounts):
            raise account_backend_errors.DuplicateAccountError(
                f"Account {account.id} already exists for address {address}"
            )
        accounts.append(account)
        wallet_private_key = self._get_wallet_private_key(address)
        self._storage.save_accounts(
            address,
            wallet_private_key,
            [entry.to_dict() for entry in accounts],
        )
        self._set_cached_accounts(address, accounts)
        return account

    def update_account(self, address: str, account: protocol_models.Account) -> protocol_models.Account:
        accounts = self._refresh_accounts_cache(address)
        for index, existing in enumerate(accounts):
            if existing.id == account.id:
                accounts[index] = account
                wallet_private_key = self._get_wallet_private_key(address)
                self._storage.save_accounts(
                    address,
                    wallet_private_key,
                    [entry.to_dict() for entry in accounts],
                )
                self._set_cached_accounts(address, accounts)
                return account
        raise account_backend_errors.AccountNotFoundError(
            f"Account {account.id} not found for address {address}"
        )

    def delete_account(self, address: str, account_id: str) -> None:
        accounts = self._refresh_accounts_cache(address)
        remaining = [account for account in accounts if account.id != account_id]
        if len(remaining) == len(accounts):
            raise account_backend_errors.AccountNotFoundError(
                f"Account {account_id} not found for address {address}"
            )
        wallet_private_key = self._get_wallet_private_key(address)
        self._storage.save_accounts(
            address,
            wallet_private_key,
            [entry.to_dict() for entry in remaining],
        )
        self._set_cached_accounts(address, remaining)
