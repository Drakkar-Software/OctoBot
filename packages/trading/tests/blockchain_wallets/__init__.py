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
import pytest

import octobot_trading.constants as constants
import octobot_trading.blockchain_wallets.blockchain_wallet_parameters as blockchain_wallet_parameters
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator


@pytest.fixture
def blockchain_descriptor_simulated():
    return blockchain_wallet_parameters.BlockchainDescriptor(
        wallet_type=blockchain_wallet_simulator.BlockchainWalletSimulator.__name__,
        network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol="ETH"
    )


@pytest.fixture
def blockchain_descriptor_real():
    return blockchain_wallet_parameters.BlockchainDescriptor(
        wallet_type="ImplementedBlockchainWallet",
        network="Ethereum",
        native_coin_symbol="ETH"
    )


@pytest.fixture
def wallet_descriptor():
    return blockchain_wallet_parameters.WalletDescriptor(
        address="0x1234567890123456789012345678901234567890",
        private_key="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    )
