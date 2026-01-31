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
import mock

import octobot_trading.blockchain_wallets
import octobot_trading.blockchain_wallets.blockchain_wallet_factory as blockchain_wallet_factory
import octobot_trading.constants as constants
import octobot_trading.errors as errors
from tests.blockchain_wallets import blockchain_descriptor_simulated, blockchain_descriptor_real, wallet_descriptor


@pytest.fixture
def mock_trader_simulate():
    trader = mock.Mock()
    trader.simulate = True
    return trader


@pytest.fixture
def mock_trader_real():
    trader = mock.Mock()
    trader.simulate = False
    return trader


def test_create_blockchain_wallet_simulated(mock_trader_simulate, blockchain_descriptor_simulated, wallet_descriptor):
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_simulated,
        wallet_descriptor=wallet_descriptor
    )
    
    wallet = octobot_trading.blockchain_wallets.create_blockchain_wallet(parameters, mock_trader_simulate)
    
    # Should return BlockchainWalletSimulator when trader is simulating
    assert isinstance(wallet, octobot_trading.blockchain_wallets.BlockchainWalletSimulator)
    assert wallet.blockchain_descriptor == blockchain_descriptor_simulated
    assert wallet.wallet_descriptor == wallet_descriptor
    assert wallet._trader == mock_trader_simulate


def test_create_blockchain_wallet_simulated_wrong_network(mock_trader_simulate, blockchain_descriptor_real, wallet_descriptor):
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_real,
        wallet_descriptor=wallet_descriptor
    )
    
    # Should raise BlockchainWalletConfigurationError when network is not SIMULATED
    with pytest.raises(errors.BlockchainWalletConfigurationError) as exc_info:
        octobot_trading.blockchain_wallets.create_blockchain_wallet(parameters, mock_trader_simulate)
    assert constants.SIMULATED_BLOCKCHAIN_NETWORK in str(exc_info.value)


def test_create_blockchain_wallet_real_trader_unsupported_blockchain(mock_trader_real, wallet_descriptor):
    blockchain_descriptor = octobot_trading.blockchain_wallets.BlockchainDescriptor(
        wallet_type="unsupported_blockchain",
        network="Ethereum",
        native_coin_symbol="ETH"
    )
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor,
        wallet_descriptor=wallet_descriptor
    )
    
    # Should raise ValueError when blockchain is not supported
    with pytest.raises(ValueError) as exc_info:
        octobot_trading.blockchain_wallets.create_blockchain_wallet(parameters, mock_trader_real)
    assert "Blockchain unsupported_blockchain not supported" in str(exc_info.value)


def test_create_blockchain_wallet_real_trader_supported_blockchain(mock_trader_real, blockchain_descriptor_real, wallet_descriptor):
    # Mock wallet class
    mock_wallet_class = mock.Mock()
    mock_wallet_instance = mock.Mock()
    mock_wallet_class.return_value = mock_wallet_instance
    
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_real,
        wallet_descriptor=wallet_descriptor
    )
    
    # Mock the wallet class lookup to return our mock wallet class
    with mock.patch.object(
        blockchain_wallet_factory, '_get_blockchain_wallet_class_by_name',
        return_value={blockchain_descriptor_real.wallet_type: mock_wallet_class}
    ):
        wallet = octobot_trading.blockchain_wallets.create_blockchain_wallet(parameters, mock_trader_real)
        
        # Should return the wallet instance from the mocked class
        assert wallet == mock_wallet_instance
        # Verify the wallet class was called with parameters
        mock_wallet_class.assert_called_once_with(parameters)
