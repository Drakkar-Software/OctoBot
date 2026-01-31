#  Drakkar-Software OctoBot-Tentacles
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
import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_trading.blockchain_wallets as blockchain_wallets


@dataclasses.dataclass
class EnsureExchangeBalanceParams(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    holdings: float


@dataclasses.dataclass
class EnsureBlockchainWalletBalanceParams(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    holdings: float
    wallet_details: blockchain_wallets.BlockchainWalletParameters # details of the wallet to transfer from


@dataclasses.dataclass
class WithdrawFundsParams(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    network: str # network to withdraw to
    address: str # recipient address of the withdrawal
    amount: typing.Optional[float] = None # defaults to all available balance if unspecified
    tag: str = ""
    params: dict = dataclasses.field(default_factory=dict) # extra parameters specific to the exchange API endpoint


@dataclasses.dataclass
class TransferFundsParams(octobot_commons.dataclasses.FlexibleDataclass):
    asset: str
    amount: float
    address: typing.Optional[str] # recipient address of the transfer
    wallet_details: blockchain_wallets.BlockchainWalletParameters # details of the wallet to transfer from
    destination_exchange: typing.Optional[str] = None # recipient address of the transfer on the exchange
