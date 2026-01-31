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
import decimal
import mock
import pytest
import pytest_asyncio
import uuid

import octobot_trading.blockchain_wallets
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data
from tests.blockchain_wallets import blockchain_descriptor_simulated, wallet_descriptor
from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting


pytestmark = pytest.mark.asyncio


@pytest.fixture
def blockchain_descriptor_with_tokens():
    token = octobot_trading.blockchain_wallets.TokenDescriptor(
        symbol="USDT",
        decimals=18,
        contract_address="0x1234567890123456789012345678901234567890"
    )
    return octobot_trading.blockchain_wallets.BlockchainDescriptor(
        wallet_type=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.__name__,
        network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol="ETH",
        tokens=[token]
    )


@pytest_asyncio.fixture
async def wallet_simulator(blockchain_descriptor_simulated, wallet_descriptor, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_simulated,
        wallet_descriptor=wallet_descriptor
    )
    return octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)


async def test_init_with_simulated_network(blockchain_descriptor_simulated, wallet_descriptor, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_simulated,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    assert wallet._trader == trader
    assert wallet.blockchain_descriptor == blockchain_descriptor_simulated
    assert wallet.wallet_descriptor == wallet_descriptor
    assert "ETH" in wallet._readonly_configured_simulated_assets
    assert wallet._readonly_configured_simulated_assets["ETH"].free == decimal.Decimal(0)


async def test_init_with_wrong_network(blockchain_descriptor_simulated, wallet_descriptor, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Create a descriptor with wrong network
    wrong_descriptor = octobot_trading.blockchain_wallets.BlockchainDescriptor(
        wallet_type=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.__name__,
        network="mainnet",  # Wrong network, should be SIMULATED_BLOCKCHAIN_NETWORK
        native_coin_symbol="ETH"
    )
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=wrong_descriptor,
        wallet_descriptor=wallet_descriptor
    )
    
    with pytest.raises(errors.BlockchainWalletConfigurationError, match="must be"):
        octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)


async def test_init_without_native_coin(wallet_descriptor, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    descriptor_no_native = octobot_trading.blockchain_wallets.BlockchainDescriptor(
        wallet_type=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.__name__,
        network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol=None
    )
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=descriptor_no_native,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    assert wallet._readonly_configured_simulated_assets == {}


async def test_get_native_coin_balance(wallet_simulator):
    balance = await wallet_simulator.get_native_coin_balance()
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal(0),
        used=decimal.Decimal(0),
        total=decimal.Decimal(0),
    )


async def test_get_native_coin_balance_with_config(wallet_simulator):
    # Configure some initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.5
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(config)
    
    balance = await wallet_simulator.get_native_coin_balance()
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("10.5"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("10.5"),
    )


async def test_get_native_coin_balance_no_native_coin(wallet_descriptor, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    descriptor_no_native = octobot_trading.blockchain_wallets.BlockchainDescriptor(
        wallet_type=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.__name__,
        network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol=None
    )
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=descriptor_no_native,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    with pytest.raises(errors.BlockchainWalletNativeCoinSymbolUndefinedError, match="Native coin symbol not found"):
        await wallet.get_native_coin_balance()


async def test_get_custom_token_balance(wallet_descriptor, blockchain_descriptor_with_tokens, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_with_tokens,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    token_descriptor = blockchain_descriptor_with_tokens.tokens[0]
    balance = await wallet.get_custom_token_balance(token_descriptor)
    
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal(0),
        used=decimal.Decimal(0),
        total=decimal.Decimal(0),
    )


async def test_get_custom_token_balance_with_config(wallet_descriptor, blockchain_descriptor_with_tokens, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_with_tokens,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    # Configure some initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "USDT",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 5.0
            }
        ]
    }
    wallet.apply_blockchain_wallet_specific_config(config)
    
    token_descriptor = blockchain_descriptor_with_tokens.tokens[0]
    balance = await wallet.get_custom_token_balance(token_descriptor)
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("5.0"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("5.0"),
    )


async def test_get_balance_with_withdrawals(wallet_simulator, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Configure initial balance
    wallet_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(wallet_config)
    
    # Add withdrawals to wallet address
    trader.exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(
        octobot_trading.personal_data.BlockchainTransaction(
            exchange_name=exchange_manager.exchange_name,
            creation_time=exchange_manager.exchange.get_exchange_current_time(),
            transaction_type=enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
            currency="ETH",
            blockchain_network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
            blockchain_transaction_id=str(uuid.uuid4()),
            blockchain_transaction_status=enums.BlockchainTransactionStatus.SUCCESS,
            source_address=wallet_simulator.wallet_descriptor.address,
            destination_address=wallet_simulator.wallet_descriptor.address,
            quantity=decimal.Decimal("2.0"),
            transaction_fee={
                enums.FeePropertyColumns.CURRENCY.value: "ETH",
                enums.FeePropertyColumns.COST.value: decimal.Decimal(0),
                enums.FeePropertyColumns.RATE.value: decimal.Decimal(0),
            },
        )
    )
    balance = await wallet_simulator.get_native_coin_balance()
    # Initial 10.0 + withdrawal 2.0 = 12.0
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("12.0"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("12.0"),
    )


async def test_get_balance_with_deposits(wallet_simulator, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Configure initial balance
    wallet_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(wallet_config)
    
    # Mock deposits from wallet address
    trader.exchange_manager.exchange_personal_data.transactions_manager.insert_transaction_instance(
        octobot_trading.personal_data.BlockchainTransaction(
            exchange_name=exchange_manager.exchange_name,
            creation_time=exchange_manager.exchange.get_exchange_current_time(),
            transaction_type=enums.TransactionType.BLOCKCHAIN_DEPOSIT,
            currency="ETH",
            blockchain_network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
            blockchain_transaction_id=str(uuid.uuid4()),
            blockchain_transaction_status=enums.BlockchainTransactionStatus.SUCCESS,
            source_address=wallet_simulator.wallet_descriptor.address,
            destination_address=wallet_simulator.wallet_descriptor.address,
            quantity=decimal.Decimal("3.0"),
            transaction_fee={},
        )
    )
    balance = await wallet_simulator.get_native_coin_balance()
    # Initial 10.0 - deposit 3.0 = 7.0
    assert balance == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("7.0"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("7.0"),
    )


async def test_transfer_native_coin(wallet_simulator):
    # Configure initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(config)
    
    amount = decimal.Decimal("1.0")
    to_address = "0xrecipient"
    
    result = await wallet_simulator.transfer_native_coin(amount, to_address)
    
    assert isinstance(result, octobot_trading.blockchain_wallets.Transaction)
    assert result.currency == "ETH"
    assert result.amount == amount
    assert result.address_from == wallet_simulator.wallet_descriptor.address
    assert result.address_to == to_address
    assert result.network == wallet_simulator.blockchain_descriptor.network
    assert result.txid is not None
    assert uuid.UUID(result.txid)  # Verify it's a valid UUID


async def test_transfer_native_coin_to_trader_deposit_address(wallet_simulator, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Configure initial balance
    wallet_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(wallet_config)
    
    amount = decimal.Decimal("1.0")
    asset = "ETH"
    
    # Get initial portfolio balance
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    initial_available = portfolio_manager.portfolio.get_currency_portfolio(asset).available
    initial_total = portfolio_manager.portfolio.get_currency_portfolio(asset).total
    
    trader_deposit_address = await trader.get_deposit_address(asset)
    trader_deposit_address = trader_deposit_address[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value]
    
    result = await wallet_simulator.transfer_native_coin(amount, trader_deposit_address)
    
    # Verify transaction was created
    assert isinstance(result, octobot_trading.blockchain_wallets.Transaction)
    assert result.currency == asset
    assert result.amount == amount
    assert result.address_to == trader_deposit_address
    
    # Verify portfolio balance was updated
    final_available = portfolio_manager.portfolio.get_currency_portfolio(asset).available
    final_total = portfolio_manager.portfolio.get_currency_portfolio(asset).total
    assert final_available == initial_available + amount
    assert final_total == initial_total + amount


async def test_transfer_native_coin_insufficient_funds(wallet_simulator):
    # Configure initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(config)
    
    amount = decimal.Decimal("20.0")  # More than available
    to_address = "0xrecipient"
    
    with pytest.raises(errors.MissingFunds) as exc_info:
        await wallet_simulator.transfer_native_coin(amount, to_address)
    assert "Not enough" in str(exc_info.value)
    assert "Available: 10" in str(exc_info.value)
    assert "required: 20" in str(exc_info.value)


async def test_transfer_custom_token(wallet_descriptor, blockchain_descriptor_with_tokens, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_with_tokens,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    # Configure initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "USDT",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 5.0
            }
        ]
    }
    wallet.apply_blockchain_wallet_specific_config(config)
    
    token_descriptor = blockchain_descriptor_with_tokens.tokens[0]
    amount = decimal.Decimal("2.0")
    to_address = "0xrecipient"
    
    result = await wallet.transfer_custom_token(token_descriptor, amount, to_address)
    
    assert isinstance(result, octobot_trading.blockchain_wallets.Transaction)
    assert result.currency == "USDT"
    assert result.amount == amount
    assert result.address_from == wallet.wallet_descriptor.address
    assert result.address_to == to_address


async def test_transfer_custom_token_insufficient_funds(wallet_descriptor, blockchain_descriptor_with_tokens, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_with_tokens,
        wallet_descriptor=wallet_descriptor
    )
    wallet = octobot_trading.blockchain_wallets.BlockchainWalletSimulator(parameters, trader)
    
    # Configure initial balance
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "USDT",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 5.0
            }
        ]
    }
    wallet.apply_blockchain_wallet_specific_config(config)
    
    token_descriptor = blockchain_descriptor_with_tokens.tokens[0]
    amount = decimal.Decimal("10.0")  # More than available
    to_address = "0xrecipient"
    
    with pytest.raises(errors.MissingFunds):
        await wallet.transfer_custom_token(token_descriptor, amount, to_address)


def test_apply_blockchain_wallet_specific_config(wallet_simulator):
    config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.5
            },
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "USDT",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 5.0
            }
        ]
    }
    
    wallet_simulator.apply_blockchain_wallet_specific_config(config)
    
    assert "ETH" in wallet_simulator._readonly_configured_simulated_assets
    assert wallet_simulator._readonly_configured_simulated_assets["ETH"] == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("10.5"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("10.5"),
    )
    assert "USDT" in wallet_simulator._readonly_configured_simulated_assets
    assert wallet_simulator._readonly_configured_simulated_assets["USDT"] == octobot_trading.blockchain_wallets.Balance(
        free=decimal.Decimal("5.0"),
        used=decimal.Decimal(0),
        total=decimal.Decimal("5.0"),
    )


async def test_withdraw_native_coin(wallet_simulator, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Configure initial balance
    wallet_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(wallet_config)
    
    with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True):
        result = await wallet_simulator.withdraw("ETH", decimal.Decimal("1.0"), constants.SIMULATED_BLOCKCHAIN_NETWORK, "0xrecipient")
        
        assert result[enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "ETH"
        assert result[enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1.0")
        assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0xrecipient"
        assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value] == wallet_simulator.wallet_descriptor.address


async def test_withdraw_disabled_funds_transfer(wallet_simulator):
    with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', False):
        with pytest.raises(errors.DisabledFundsTransferError, match="Funds transfer is not enabled"):
            await wallet_simulator.withdraw("ETH", decimal.Decimal("1.0"), constants.SIMULATED_BLOCKCHAIN_NETWORK, "0xrecipient")


async def test_get_balance_with_withdrawals_and_deposits(wallet_simulator, backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    # Configure initial balance
    wallet_config = {
        blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
            {
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: 10.0
            }
        ]
    }
    wallet_simulator.apply_blockchain_wallet_specific_config(wallet_config)
    
    # Mock withdrawals and deposits
    mock_withdrawal = mock.Mock()
    mock_withdrawal.quantity = decimal.Decimal("3.0")
    mock_deposit = mock.Mock()
    mock_deposit.quantity = decimal.Decimal("2.0")
    
    def get_transactions(**kwargs):
        if kwargs.get("destination_address") == wallet_simulator.wallet_descriptor.address:
            return [mock_withdrawal]
        elif kwargs.get("source_address") == wallet_simulator.wallet_descriptor.address:
            return [mock_deposit]
        return []
    
    trader.exchange_manager.exchange_personal_data.transactions_manager.get_blockchain_transactions = mock.Mock(
        side_effect=get_transactions
    )
    
    balance = await wallet_simulator.get_native_coin_balance()
    # Initial 10.0 + withdrawal 3.0 - deposit 2.0 = 11.0
    assert balance.free == decimal.Decimal("11.0")


async def test_get_deposit_address(wallet_simulator):
    result = await wallet_simulator.get_deposit_address("ETH")
    
    assert result[enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value] == "ETH"
    assert result[enums.ExchangeConstantsDepositAddressColumns.NETWORK.value] == wallet_simulator.blockchain_descriptor.network
    assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == wallet_simulator.wallet_descriptor.address
