#  This file is part of OctoBot Sync (https://github.com/Drakkar-Software/OctoBot)
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

from dataclasses import dataclass

import web3


@dataclass
class Wallet:
    private_key: str
    address: str


def create_evm_wallet() -> Wallet:
    account = web3.Account.create()  # pylint: disable=no-value-for-parameter
    return Wallet(private_key=account.key.hex(), address=account.address)


def create_evm_wallet_with_mnemonic() -> tuple[Wallet, str]:
    web3.Account.enable_unaudited_hdwallet_features()  # pylint: disable=no-value-for-parameter
    account, mnemonic = web3.Account.create_with_mnemonic()  # pylint: disable=no-value-for-parameter
    return Wallet(private_key=account.key.hex(), address=account.address), mnemonic


def wallet_from_mnemonic(mnemonic: str) -> Wallet:
    web3.Account.enable_unaudited_hdwallet_features()  # pylint: disable=no-value-for-parameter
    account = web3.Account.from_mnemonic(mnemonic)  # pylint: disable=no-value-for-parameter
    return Wallet(private_key=account.key.hex(), address=account.address)


def address_from_evm_key(private_key: str) -> str:
    return web3.Account.from_key(private_key).address  # pylint: disable=no-value-for-parameter
