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
import pytest
import mock
import uuid

import octobot_commons.tests.test_config as test_config
import octobot_trading.exchanges
import octobot_trading.constants as constants
import octobot_trading.enums as enums


@pytest.fixture
def trader_simulator():
    exchange_manager = mock.Mock(
        exchange_name="test_exchange",
    )
    return octobot_trading.exchanges.TraderSimulator(test_config.load_test_config(), exchange_manager)


def test_constructor(trader_simulator):
    assert isinstance(trader_simulator, octobot_trading.exchanges.TraderSimulator)
    assert trader_simulator.exchange_manager.exchange_name == "test_exchange"
    assert trader_simulator.simulate is True


@pytest.mark.asyncio
async def test_get_deposit_address(trader_simulator):
    asset = "BTC"
    
    result = await trader_simulator.get_deposit_address(asset)
    
    # Verify the structure and values
    assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == f"{constants.SIMULATED_DEPOSIT_ADDRESS}_{asset}"
    assert result[enums.ExchangeConstantsDepositAddressColumns.TAG.value] == ""
    assert result[enums.ExchangeConstantsDepositAddressColumns.NETWORK.value] == constants.SIMULATED_BLOCKCHAIN_NETWORK
    assert result[enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value] == asset
    
    # Test with different asset
    asset = "ETH"
    result = await trader_simulator.get_deposit_address(asset)
    assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == f"{constants.SIMULATED_DEPOSIT_ADDRESS}_{asset}"
    assert result[enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value] == asset


@pytest.mark.asyncio
async def test_withdraw_on_exchange(trader_simulator):
    asset = "BTC"
    amount = decimal.Decimal("0.1")
    network = "bitcoin"
    address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    tag = "test_tag"
    params = {"network": "bitcoin"}
    
    result = await trader_simulator._withdraw_on_exchange(asset, amount, network, address, tag=tag, params=params)
    
    # Verify withdrawal data structure
    assert enums.ExchangeConstantsTransactionColumns.TXID.value in result
    assert enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value in result
    assert enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value in result
    assert enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value in result
    assert enums.ExchangeConstantsTransactionColumns.AMOUNT.value in result
    assert enums.ExchangeConstantsTransactionColumns.CURRENCY.value in result
    assert enums.ExchangeConstantsTransactionColumns.ID.value in result
    assert enums.ExchangeConstantsTransactionColumns.FEE.value in result
    assert enums.ExchangeConstantsTransactionColumns.STATUS.value in result
    assert enums.ExchangeConstantsTransactionColumns.TAG.value in result
    assert enums.ExchangeConstantsTransactionColumns.TYPE.value in result
    assert enums.ExchangeConstantsTransactionColumns.NETWORK.value in result
    
    # Verify values
    assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == address
    assert result[enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == amount
    assert result[enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == asset
    assert result[enums.ExchangeConstantsTransactionColumns.TAG.value] == tag
    assert result[enums.ExchangeConstantsTransactionColumns.FEE.value] == {
        enums.FeePropertyColumns.RATE.value: constants.ZERO,
        enums.FeePropertyColumns.COST.value: constants.ZERO,
        enums.FeePropertyColumns.CURRENCY.value: asset,
    }
    assert result[enums.ExchangeConstantsTransactionColumns.STATUS.value] == enums.BlockchainTransactionStatus.SUCCESS.value
    assert result[enums.ExchangeConstantsTransactionColumns.TYPE.value] == enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value
    assert result[enums.ExchangeConstantsTransactionColumns.NETWORK.value] == "bitcoin"
    
    # Verify TXID and ID are valid UUIDs (they should be the same)
    txid = result[enums.ExchangeConstantsTransactionColumns.TXID.value]
    transaction_id = result[enums.ExchangeConstantsTransactionColumns.ID.value]
    assert txid == transaction_id
    # Verify it's a valid UUID format
    uuid.UUID(txid)
    
    # Verify ADDRESS_FROM matches the deposit address
    deposit_address = await trader_simulator.get_deposit_address(asset)
    assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value] == deposit_address[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value]
    
    # Test without tag
    result_no_tag = await trader_simulator._withdraw_on_exchange(asset, amount, network, address)
    assert result_no_tag[enums.ExchangeConstantsTransactionColumns.TAG.value] == ""
