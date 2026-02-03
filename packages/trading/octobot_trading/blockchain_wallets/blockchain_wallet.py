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
import asyncio

import octobot_commons.logging as commons_logging
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.blockchain_wallets.blockchain_wallet_parameters as blockchain_wallet_parameters
import octobot_trading.accounts
import octobot_trading.blockchain_wallets.adapter as blockchain_wallet_adapter


class BlockchainWallet(octobot_trading.accounts.AbstractAccount):
    """
    Base class for all blockchain wallets, to be implemented by specific blockchain wallet subclasses.
    """
    ADAPTER_CLASS = blockchain_wallet_adapter.BlockchainWalletAdapter

    def __init__(self, parameters: blockchain_wallet_parameters.BlockchainWalletParameters):
        super().__init__()
        self.blockchain_descriptor: blockchain_wallet_parameters.BlockchainDescriptor = parameters.blockchain_descriptor
        self.wallet_descriptor: blockchain_wallet_parameters.WalletDescriptor = parameters.wallet_descriptor
        self.adapter = self.ADAPTER_CLASS(self)
        self.logger: commons_logging.BotLogger = commons_logging.get_logger(
            f"{self.__class__.__name__}[{self.blockchain_descriptor.network}]"
        )
        if self.wallet_descriptor.specific_config :
            self.apply_blockchain_wallet_specific_config(self.wallet_descriptor.specific_config)

    async def get_balance(self, **kwargs: dict) -> dict[str, dict]:
        balances = {
            self.blockchain_descriptor.native_coin_symbol: await self.get_native_coin_balance()
        } if self.blockchain_descriptor.native_coin_symbol else {}
        if self.blockchain_descriptor.tokens:
            await asyncio.gather(*[
                self._populate_custom_token_balance(balances, token_descriptor)
                for token_descriptor in self.blockchain_descriptor.tokens
            ])
        return self.adapter.adapt_balance(balances)

    async def _populate_custom_token_balance(
        self,
        balances: dict[str, blockchain_wallet_adapter.Balance],
        token_descriptor: blockchain_wallet_parameters.TokenDescriptor
    ):
        balances[token_descriptor.symbol] = await self.get_custom_token_balance(token_descriptor)

    async def withdraw(
        self, 
        asset: str, 
        amount: decimal.Decimal, 
        network: str,
        address: str, 
    ) -> dict:
        if not constants.ALLOW_FUNDS_TRANSFER:
            raise errors.DisabledFundsTransferError("Funds transfer is not enabled")
        self.logger.info(f"Transferring {amount} {asset} from {self.wallet_descriptor.address} to {address}")
        if asset == self.blockchain_descriptor.native_coin_symbol:
            transaction = await self.transfer_native_coin(amount, address)
        else:
            transaction = await self.transfer_custom_token(self._get_token_descriptor(asset), amount, address)
        return self.adapter.adapt_transaction(transaction)

    async def get_deposit_address(self, asset: str, params: dict = None) -> dict:
        return self.adapter.adapt_deposit_address(
            blockchain_wallet_adapter.DepositAddress(
                currency=asset,
                network=self.blockchain_descriptor.network,
                address=self.wallet_descriptor.address,
            )
        )


    def apply_blockchain_wallet_specific_config(self, specific_config: dict):
        # implement if necessary
        self.logger.error(
            f"Incomplete implementation: apply_blockchain_wallet_specific_config is not "
            f"implemented to handle configuration for {self.__class__.__name__} blockchain wallet. "
            f"Ignored given configuration."
        )

    async def get_native_coin_balance(self) -> blockchain_wallet_adapter.Balance:
        raise NotImplementedError("get_native_coin_balance is not implemented")

    async def get_custom_token_balance(self, token_descriptor: blockchain_wallet_parameters.TokenDescriptor) -> blockchain_wallet_adapter.Balance:
        raise NotImplementedError("get_custom_token_balance is not implemented")

    async def transfer_native_coin(self, amount: decimal.Decimal, to_address: str) -> blockchain_wallet_adapter.Transaction:
        raise NotImplementedError("transfer_native_coin is not implemented")

    async def transfer_custom_token(
        self,
        token_descriptor: blockchain_wallet_parameters.TokenDescriptor,
        amount: decimal.Decimal,
        to_address: str,
    ) -> blockchain_wallet_adapter.Transaction:
        raise NotImplementedError("transfer_custom_token is not implemented")

    def _get_token_descriptor(self, token_symbol: str) -> blockchain_wallet_parameters.TokenDescriptor:
        for token_parameter in self.blockchain_descriptor.tokens:
            if token_parameter.symbol == token_symbol:
                return token_parameter
        raise KeyError(
            f"Token {token_symbol} not found in {self.__class__.__name__} "
            f"wallet's {len(self.blockchain_descriptor.tokens)} pre-configured tokens."
        )
