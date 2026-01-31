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
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


@functools.lru_cache(maxsize=1)
def _get_blockchain_wallet_class_by_name() -> dict[str, type[blockchain_wallet.BlockchainWallet]]:
    # cached to avoid re-scanning the tentacles for each wallet creation
    return {
        wallet_class.__name__: wallet_class 
        for wallet_class in tentacles_management.get_all_classes_from_parent(blockchain_wallet.BlockchainWallet)
    }


def create_blockchain_wallet(
    parameters: blockchain_wallet_parameters.BlockchainWalletParameters,
    trader: "octobot_trading.exchanges.Trader",
) -> blockchain_wallet.BlockchainWallet:
    """
    Create a wallet of the given type
    :param parameters: the parameters of the wallet to create
    :return: the created wallet
    """
    if trader.simulate:
        # use simulator wallet with trader callbacks to interact with simulated exchange wallet
        return blockchain_wallet_simulator.BlockchainWalletSimulator(parameters, trader=trader)
    try:
        return _get_blockchain_wallet_class_by_name()[parameters.blockchain_descriptor.wallet_type](parameters)
    except KeyError as err:
        raise ValueError(f"Blockchain {parameters.blockchain_descriptor.wallet_type} not supported") from err
