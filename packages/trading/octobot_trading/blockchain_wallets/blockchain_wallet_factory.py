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
import functools
import typing

import octobot_commons.tentacles_management as tentacles_management
import octobot_trading.blockchain_wallets.blockchain_wallet as blockchain_wallet
import octobot_trading.blockchain_wallets.blockchain_wallet_parameters as blockchain_wallet_parameters

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


@functools.lru_cache(maxsize=1)
def get_blockchain_wallet_class_by_blockchain() -> dict[str, type[blockchain_wallet.BlockchainWallet]]:
    # cached to avoid re-scanning the tentacles for each wallet creation
    return {
        wallet_class.BLOCKCHAIN: wallet_class 
        for wallet_class in tentacles_management.get_all_classes_from_parent(blockchain_wallet.BlockchainWallet)
    }


def create_blockchain_wallet(
    parameters: blockchain_wallet_parameters.BlockchainWalletParameters,
    trader: typing.Optional["octobot_trading.exchanges.Trader"],
) -> blockchain_wallet.BlockchainWallet:
    """
    Create a wallet of the given type
    :param parameters: the parameters of the wallet to create
    :return: the created wallet
    """
    blockchain_wallet_class = None
    try:
        blockchain_wallet_class = get_blockchain_wallet_class_by_blockchain()[
            parameters.blockchain_descriptor.blockchain
        ]
        try:
            return blockchain_wallet_class(parameters)
        except TypeError:
            # trader arg is required for this wallet
            return blockchain_wallet_class(parameters, trader=trader)
    except KeyError as err:
        raise ValueError(
            f"Blockchain {parameters.blockchain_descriptor.blockchain} not supported"
        ) from err
