#  Drakkar-Software OctoBot-Commons
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
import pytest_asyncio

import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.constants
import octobot_trading.enums
import octobot_trading.errors
import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.blockchain_wallets.simulator.blockchain_wallet_simulator as blockchain_wallet_simulator

import tentacles.Meta.DSL_operators.blockchain_wallet_operators.blockchain_wallet_ops as blockchain_wallet_ops

from tentacles.Meta.DSL_operators.exchange_operators.tests import (
    backtesting_config,
    fake_backtesting,
    backtesting_exchange_manager,
    backtesting_trader,
)


BLOCKCHAIN_DESCRIPTOR = {
    "blockchain": blockchain_wallets.BlockchainWalletSimulator.BLOCKCHAIN,
    "network": octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK,
    "native_coin_symbol": "ETH",
}
WALLET_DESCRIPTOR = {"address": "0x1234567890123456789012345678901234567890"}


def _wallet_descriptor_with_eth_balance(amount: float):
    return {
        **WALLET_DESCRIPTOR,
        "specific_config": {
            blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: [
                {
                    blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.ASSET.value: "ETH",
                    blockchain_wallet_simulator.BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: amount,
                }
            ]
        },
    }


@pytest_asyncio.fixture
async def blockchain_wallet_operators(backtesting_trader):
    _config, exchange_manager, _trader = backtesting_trader
    return blockchain_wallet_ops.create_blockchain_wallet_operators(exchange_manager)


@pytest_asyncio.fixture
async def interpreter(blockchain_wallet_operators):
    return dsl_interpreter.Interpreter(
        dsl_interpreter.get_all_operators()
        + blockchain_wallet_operators
    )


class TestBlockchainWalletBalanceOperator:
    @pytest.mark.asyncio
    async def test_pre_compute(self, blockchain_wallet_operators):
        balance_op_class, _ = blockchain_wallet_operators

        operator = balance_op_class(
            BLOCKCHAIN_DESCRIPTOR,
            _wallet_descriptor_with_eth_balance(1.5),
            "ETH",
        )
        await operator.pre_compute()
        assert operator.value == 1.5

    @pytest.mark.asyncio
    async def test_pre_compute_asset_not_in_balance(self, blockchain_wallet_operators):
        balance_op_class, _ = blockchain_wallet_operators

        operator = balance_op_class(
            BLOCKCHAIN_DESCRIPTOR,
            _wallet_descriptor_with_eth_balance(10.0),
            "BTC",
        )
        await operator.pre_compute()
        assert operator.value == float(octobot_trading.constants.ZERO)

    def test_compute_without_pre_compute(self, blockchain_wallet_operators):
        balance_op_class, _ = blockchain_wallet_operators
        operator = balance_op_class(BLOCKCHAIN_DESCRIPTOR, WALLET_DESCRIPTOR, "BTC")
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="has not been pre_computed",
        ):
            operator.compute()

    @pytest.mark.asyncio
    async def test_blockchain_wallet_balance_call_as_dsl(self, interpreter):
        blockchain_descriptor = BLOCKCHAIN_DESCRIPTOR
        wallet_descriptor = _wallet_descriptor_with_eth_balance(1.5)
        assert await interpreter.interprete(
            f"blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, 'ETH')"
        ) == 1.5
        assert await interpreter.interprete(
            f"blockchain_wallet_balance({blockchain_descriptor}, {wallet_descriptor}, 'BTC')"
        ) == 0.0


class TestBlockchainWalletTransferOperator:
    @pytest.mark.asyncio
    async def test_pre_compute_with_address(self, blockchain_wallet_operators):
        _, transfer_op_class = blockchain_wallet_operators

        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
        operator = transfer_op_class(
            BLOCKCHAIN_DESCRIPTOR,
            _wallet_descriptor_with_eth_balance(10.0),
            "ETH",
            0.1,
            address="0xrecipient123",
        )
        await operator.pre_compute()
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

        assert operator.value is not None
        assert isinstance(operator.value, dict)
        assert "created_transactions" in operator.value
        assert len(operator.value["created_transactions"]) == 1
        tx = operator.value["created_transactions"][0]
        assert octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value in tx

    @pytest.mark.asyncio
    async def test_pre_compute_with_destination_exchange(self, blockchain_wallet_operators):
        _, transfer_op_class = blockchain_wallet_operators

        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
        operator = transfer_op_class(
            BLOCKCHAIN_DESCRIPTOR,
            _wallet_descriptor_with_eth_balance(10.0),
            "ETH",
            0.5,
            destination_exchange="binanceus",
        )
        await operator.pre_compute()
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False

        assert operator.value is not None
        assert isinstance(operator.value, dict)
        assert "created_transactions" in operator.value
        assert len(operator.value["created_transactions"]) == 1
        tx = operator.value["created_transactions"][0]
        assert octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value in tx

    @pytest.mark.asyncio
    async def test_pre_compute_unsupported_destination_exchange(self, blockchain_wallet_operators):
        _, transfer_op_class = blockchain_wallet_operators

        operator = transfer_op_class(
            BLOCKCHAIN_DESCRIPTOR,
            WALLET_DESCRIPTOR,
            "BTC",
            0.1,
            destination_exchange="unknown_exchange",
        )
        with pytest.raises(
            octobot_commons.errors.DSLInterpreterError,
            match="Unsupported destination exchange: unknown_exchange",
        ):
            await operator.pre_compute()

    @pytest.mark.asyncio
    async def test_blockchain_wallet_transfer_call_as_dsl(self, interpreter):
        blockchain_descriptor = BLOCKCHAIN_DESCRIPTOR
        wallet_descriptor = _wallet_descriptor_with_eth_balance(1.5)
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = False
        with pytest.raises(
            octobot_trading.errors.DisabledFundsTransferError,
            match="Funds transfer is not enabled",
        ):
            await interpreter.interprete(
                f"blockchain_wallet_transfer({blockchain_descriptor}, {wallet_descriptor}, 'ETH', 0.1, address='0xrecipient123')"
            )
        octobot_trading.constants.ALLOW_FUNDS_TRANSFER = True
        result = await interpreter.interprete(
            f"blockchain_wallet_transfer({blockchain_descriptor}, {wallet_descriptor}, 'ETH', 0.1, address='0xrecipient123')"
        )
        assert "created_transactions" in result
        assert len(result["created_transactions"]) == 1
        tx = result["created_transactions"][0]
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.TXID.value]
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value] == "0x1234567890123456789012345678901234567890"
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0xrecipient123"
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal('0.1')
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "ETH"
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.FEE.value] is None
        assert tx[octobot_trading.enums.ExchangeConstantsTransactionColumns.INTERNAL.value] is False
        result = await interpreter.interprete(
            f"blockchain_wallet_transfer({blockchain_descriptor}, {wallet_descriptor}, 'ETH', 0.1, destination_exchange='binanceus')"
        )
        assert result and isinstance(result, dict)
        assert "created_transactions" in result
