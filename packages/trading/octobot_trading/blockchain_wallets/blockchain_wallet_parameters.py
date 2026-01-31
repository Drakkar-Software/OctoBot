#  Drakkar-Software OctoBot-Trading
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


@dataclasses.dataclass
class TokenDescriptor(octobot_commons.dataclasses.FlexibleDataclass):
    """
    Descriptor of a token that is not the native coin of a blockchain
    """
    symbol: str # ex: "USDT" for USDT on Ethereum
    decimals: int # ex: 18 for USDT on Ethereum
    contract_address: str # ex: "0xdAC17F958D2ee523a2206206994597C13D831ec7" for USDT on Ethereum


@dataclasses.dataclass
class BlockchainDescriptor(octobot_commons.dataclasses.FlexibleDataclass):
    """
    Descriptor for a blockchain
    """
    wallet_type: str # name of the BlockchainWallet subclass to use for this blockchain
    # network: configured network of the blockchain, ex: "Ethereum" or "Polygon Mainnet".
    # This value is used for internal references and logs.
    # The network connection details (such as the RPC URL) are defined in the specific_config attribute.
    network: str
    native_coin_symbol: typing.Optional[str] = None # ex: "ETH" for Ethereum
    specific_config: typing.Optional[dict[str, typing.Any]] = None # ex: {"rpc_url": "https://...."} for Ethereum
    # Define tokens in case this blockchain supports it (ex: ERC20 tokens on Ethereum).
    # A token must be defined for its balance to be tracked and to be able to transfer it.
    tokens: list[TokenDescriptor] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.tokens and isinstance(self.tokens[0], dict):
            self.tokens = [TokenDescriptor.from_dict(token) for token in self.tokens]


@dataclasses.dataclass
class WalletDescriptor(octobot_commons.dataclasses.FlexibleDataclass):
    """
    Descriptor for a wallet to use for this blockchain
    """
    address: str # public address of the wallet
    private_key: typing.Optional[str] = None # private key of the wallet
    # extra configuration for the user's wallet, notably used to initialize simulator wallets holdings
    specific_config: typing.Optional[dict[str, typing.Any]] = None


@dataclasses.dataclass
class BlockchainWalletParameters(octobot_commons.dataclasses.FlexibleDataclass):
    """
    Parameters for a blockchain wallet
    """
    blockchain_descriptor: BlockchainDescriptor
    wallet_descriptor: WalletDescriptor

    def __post_init__(self):
        if self.blockchain_descriptor and isinstance(self.blockchain_descriptor, dict):
            self.blockchain_descriptor = BlockchainDescriptor.from_dict(self.blockchain_descriptor)
        if self.wallet_descriptor and isinstance(self.wallet_descriptor, dict):
            self.wallet_descriptor = WalletDescriptor.from_dict(self.wallet_descriptor)
