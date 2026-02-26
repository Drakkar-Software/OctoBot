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
import typing
import dataclasses
import decimal

import octobot_commons.dataclasses
import octobot_commons.errors
import octobot_commons.dsl_interpreter as dsl_interpreter
import octobot_trading.exchanges
import octobot_trading.api
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.blockchain_wallets as blockchain_wallets


@dataclasses.dataclass
class BlockchainWalletBalanceParams(octobot_commons.dataclasses.FlexibleDataclass):
    blockchain_descriptor: blockchain_wallets.BlockchainDescriptor # descriptor of the blockchain to use
    wallet_descriptor: blockchain_wallets.WalletDescriptor # descriptor of the wallet to use
    asset: str


@dataclasses.dataclass
class TransferFundsParams(octobot_commons.dataclasses.FlexibleDataclass):
    blockchain_descriptor: blockchain_wallets.BlockchainDescriptor # descriptor of the blockchain to use
    wallet_descriptor: blockchain_wallets.WalletDescriptor # descriptor of the wallet to use
    asset: str
    amount: float
    address: typing.Optional[str] = None # recipient address of the transfer
    destination_exchange: typing.Optional[str] = None # recipient address of the transfer on the exchange


BLOCKCHAIN_WALLET_LIBRARY = "blockchain_wallet"


class BlockchainWalletOperator(dsl_interpreter.PreComputingCallOperator):
    @staticmethod
    def get_library() -> str:
        # this is a contextual operator, so it should not be included by default in the get_all_operators function return values
        return BLOCKCHAIN_WALLET_LIBRARY

    @classmethod
    def get_blockchain_wallet_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
        return [
            dsl_interpreter.OperatorParameter(name="blockchain_descriptor", description="descriptor of the blockchain to use as in octobot_trading.blockchain_wallets.BlockchainDescriptor", required=True, type=dict),
            dsl_interpreter.OperatorParameter(name="wallet_descriptor", description="descriptor of the wallet to use as in octobot_trading.blockchain_wallets.WalletDescriptor", required=True, type=dict),
        ]


def create_blockchain_wallet_operators(
    exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager],
) -> typing.List[type[BlockchainWalletOperator]]:

    class _BlockchainWalletBalanceOperator(BlockchainWalletOperator):
        DESCRIPTION = "Returns the balance of the asset in the blockchain wallet"
        EXAMPLE = "blockchain_wallet_balance('BTC')"

        @staticmethod
        def get_name() -> str:
            return "blockchain_wallet_balance"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                *cls.get_blockchain_wallet_parameters(),
                dsl_interpreter.OperatorParameter(name="asset", description="the asset to get the balance for", required=True, type=str),
            ]

        async def pre_compute(self) -> None:
            await super().pre_compute()
            param_by_name = self.get_computed_value_by_parameter()
            blockchain_wallet_balance_params = BlockchainWalletBalanceParams.from_dict(param_by_name)
            async with octobot_trading.api.blockchain_wallet_context(
                blockchain_wallets.BlockchainWalletParameters(
                    blockchain_descriptor=blockchain_wallet_balance_params.blockchain_descriptor,
                    wallet_descriptor=blockchain_wallet_balance_params.wallet_descriptor,
                ), 
                exchange_manager.trader
            ) as wallet:
                wallet_balance = await wallet.get_balance()
                self.value = float(
                    wallet_balance[blockchain_wallet_balance_params.asset][
                        octobot_trading.constants.CONFIG_PORTFOLIO_FREE
                    ] if blockchain_wallet_balance_params.asset in wallet_balance else octobot_trading.constants.ZERO
                )

    class _BlockchainWalletTransferOperator(BlockchainWalletOperator):
        DESCRIPTION = "Withdraws an asset from the exchange's portfolio. requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)"
        EXAMPLE = "blockchain_wallet_transfer('BTC', 'ethereum', '0x1234567890abcdef1234567890abcdef12345678', 0.1)"

        @staticmethod
        def get_name() -> str:
            return "blockchain_wallet_transfer"

        @classmethod
        def get_parameters(cls) -> list[dsl_interpreter.OperatorParameter]:
            return [
                *cls.get_blockchain_wallet_parameters(),
                dsl_interpreter.OperatorParameter(name="asset", description="the asset to transfer", required=True, type=str),
                dsl_interpreter.OperatorParameter(name="amount", description="the amount to transfer", required=True, type=float),
                dsl_interpreter.OperatorParameter(name="address", description="the address to transfer to", required=False, type=str, default=None),
                dsl_interpreter.OperatorParameter(name="destination_exchange", description="the exchange to transfer to", required=False, type=str, default=None),
            ]

        async def pre_compute(self) -> None:
            await super().pre_compute()
            param_by_name = self.get_computed_value_by_parameter()
            transfer_funds_params = TransferFundsParams.from_dict(param_by_name)
            async with octobot_trading.api.blockchain_wallet_context(
                blockchain_wallets.BlockchainWalletParameters(
                    blockchain_descriptor=transfer_funds_params.blockchain_descriptor,
                    wallet_descriptor=transfer_funds_params.wallet_descriptor,
                ), 
                exchange_manager.trader
            ) as wallet:
                if transfer_funds_params.address:
                    address = transfer_funds_params.address
                elif transfer_funds_params.destination_exchange == exchange_manager.exchange_name:
                    address = (
                        await exchange_manager.trader.get_deposit_address(transfer_funds_params.asset)
                    )[octobot_trading.enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value]
                else:
                    raise octobot_commons.errors.DSLInterpreterError(
                        f"Unsupported destination exchange: {transfer_funds_params.destination_exchange}"
                    )
                # requires ALLOW_FUNDS_TRANSFER env to be True (disabled by default to protect funds)
                self.value = await wallet.withdraw(
                    transfer_funds_params.asset,
                    decimal.Decimal(str(transfer_funds_params.amount)),
                    transfer_funds_params.blockchain_descriptor.network,
                    address,
                )

    return [_BlockchainWalletBalanceOperator, _BlockchainWalletTransferOperator]
