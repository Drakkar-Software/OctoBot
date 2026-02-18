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
import typing
import enum
import decimal
import uuid

import octobot_commons.enums as commons_enums
import octobot_trading.errors
import octobot_trading.enums
import octobot_trading.constants
import octobot_trading.blockchain_wallets.blockchain_wallet as blockchain_wallet
import octobot_trading.blockchain_wallets.adapter as blockchain_wallet_adapter
import octobot_trading.blockchain_wallets.blockchain_wallet_parameters as blockchain_wallet_parameters

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class BlockchainWalletSimulatorConfigurationKeys(enum.Enum):
    ASSETS = "assets"
    ASSET = "asset"
    AMOUNT = "amount"


class BlockchainWalletSimulator(blockchain_wallet.BlockchainWallet):
    """
    Simulator for a blockchain wallet: can deposit coins on the given trader's portfolio
    and receive withdrawals when done to its address or to the trader's simulated withdrawal address.
    This wallet keeps track of the simulated assets balances using its initial configuration on top of 
    which it adds the deposits and withdrawals associated to the wallet's address.
    Deposits and withdrawals are tracked using the trader's transactions manager.

    This wallet is stateless: it can be re-created at any time as its state only 
    depends on its initial configuration and the trader's transactions history.
    """
    def __init__(
        self,
        parameters: blockchain_wallet_parameters.BlockchainWalletParameters,
        trader: "octobot_trading.exchanges.Trader"
    ):
        if parameters.blockchain_descriptor.network != octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK:
            # this is a simulator wallet, the network must be the simulated network 
            # to ensure compatibility with simulated trader withdrawals
            raise octobot_trading.errors.BlockchainWalletConfigurationError(
                f"Simulated blockchain {self.__class__.__name__} configured network "
                f"must be {octobot_trading.constants.SIMULATED_BLOCKCHAIN_NETWORK}, "
                f"got {parameters.blockchain_descriptor.network}"
            )
        self._readonly_configured_simulated_assets: typing.Dict[str, blockchain_wallet_adapter.Balance] = {
            parameters.blockchain_descriptor.native_coin_symbol: blockchain_wallet_adapter.Balance(
                free=decimal.Decimal(0)
            )
        } if parameters.blockchain_descriptor.native_coin_symbol else {}
        self._trader: "octobot_trading.exchanges.Trader" = trader
        super().__init__(parameters)

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        """
        Called at constructor, should define all the blockchain wallet's user inputs.
        """
        assets = [{
            BlockchainWalletSimulatorConfigurationKeys.ASSETS.value: cls.CLASS_UI.user_input(
                BlockchainWalletSimulatorConfigurationKeys.ASSETS.value, commons_enums.UserInputTypes.TEXT, "ETH", inputs,
                parent_input_name=BlockchainWalletSimulatorConfigurationKeys.ASSETS.value,
                title=f"Name of the assets to simulate in wallet.",
            ),
            BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value: cls.CLASS_UI.user_input(
                BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value, commons_enums.UserInputTypes.FLOAT, 12.34, inputs,
                min_val=0,
                parent_input_name=BlockchainWalletSimulatorConfigurationKeys.ASSETS.value,
                title=f"Amount of the asset to simulate in wallet."
            )
        }]
        cls.CLASS_UI.user_input(
            BlockchainWalletSimulatorConfigurationKeys.ASSETS, commons_enums.UserInputTypes.OBJECT_ARRAY, assets, inputs,
            other_schema_values={"minItems": 0, "uniqueItems": True},
            item_title="Asset",
            title="Assets to simulate in wallet",
        )

    async def get_native_coin_balance(self) -> blockchain_wallet_adapter.Balance:
        self._ensure_native_coin_symbol()
        return self._get_token_balance(self.blockchain_descriptor.native_coin_symbol) # type: ignore

    async def get_custom_token_balance(self, token_descriptor: blockchain_wallet_parameters.TokenDescriptor) -> blockchain_wallet_adapter.Balance:
        return self._get_token_balance(token_descriptor.symbol)

    async def transfer_native_coin(self, amount: decimal.Decimal, to_address: str) -> blockchain_wallet_adapter.Transaction:
        self._ensure_native_coin_symbol()
        return await self._transfer_coin(
            self.blockchain_descriptor.native_coin_symbol, amount, to_address
        ) # type: ignore

    async def transfer_custom_token(self, token_descriptor: blockchain_wallet_parameters.TokenDescriptor, amount: decimal.Decimal, to_address: str) -> blockchain_wallet_adapter.Transaction:
        return await self._transfer_coin(token_descriptor.symbol, amount, to_address)

    def _ensure_native_coin_symbol(self):
        if not self.blockchain_descriptor.native_coin_symbol:
            raise octobot_trading.errors.BlockchainWalletNativeCoinSymbolUndefinedError(
                f"Native coin symbol not found in {self.__class__.__name__} blockchain descriptor"
            )

    def apply_blockchain_wallet_specific_config(self, specific_config: dict):
        """
        Used to populate the simulated blockchain wallet holdings
        """
        for asset in specific_config[BlockchainWalletSimulatorConfigurationKeys.ASSETS.value]:
            self._readonly_configured_simulated_assets[asset[BlockchainWalletSimulatorConfigurationKeys.ASSET.value]] = blockchain_wallet_adapter.Balance(
                free=decimal.Decimal(asset[BlockchainWalletSimulatorConfigurationKeys.AMOUNT.value]),
            )

    def _get_token_balance(self, asset: str) -> blockchain_wallet_adapter.Balance:
        base_free_balance = (
            self._readonly_configured_simulated_assets[asset].free 
            if asset in self._readonly_configured_simulated_assets 
            else octobot_trading.constants.ZERO
        )
        total_withdrawals_to_this_address = self._get_total_withdrawals_to_address(
            asset, self.wallet_descriptor.address
        )
        total_deposits_from_this_address = self._get_total_deposits_from_address(
            asset, self.wallet_descriptor.address
        )
        return blockchain_wallet_adapter.Balance(
            free=base_free_balance + total_withdrawals_to_this_address - total_deposits_from_this_address,
        )

    async def _get_trader_deposit_address(self, asset: str) -> str:
        return (await self._trader.get_deposit_address(asset))[
            octobot_trading.enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value
        ]

    async def _transfer_coin(
        self, asset: str, amount: decimal.Decimal, to_address: str
    ) -> blockchain_wallet_adapter.Transaction:
        holdings = self._get_token_balance(asset)
        if amount > holdings.free:
            raise octobot_trading.errors.MissingFunds(
                f"Not enough {asset} available in simulated assets. "
                f"Available: {holdings.free}, required: {amount}"
            )
        transaction_id = str(uuid.uuid4())
        if to_address == await self._get_trader_deposit_address(asset):
            # this is an exchange deposit: credit the exchange portfolio
            await self._deposit_coin_on_trader_portfolio(asset, amount, to_address, transaction_id)

        return blockchain_wallet_adapter.Transaction(
            txid=transaction_id,
            timestamp=self._trader.exchange_manager.exchange.get_exchange_current_time(),
            address_from=self.wallet_descriptor.address,
            network=self.blockchain_descriptor.network,
            address_to=to_address,
            amount=amount,
            currency=asset,
        )

    async def _deposit_coin_on_trader_portfolio(
        self, asset: str, amount: decimal.Decimal, destination_address: str, transaction_id: str
    ):
        await self._trader.exchange_manager.exchange_personal_data.handle_portfolio_update_from_deposit(
            asset,
            amount,
            self.blockchain_descriptor.network,
            transaction_id,
            destination_address,
            transaction_status=octobot_trading.enums.BlockchainTransactionStatus.SUCCESS,
            source_address=self.wallet_descriptor.address,
            transaction_fee={
                octobot_trading.enums.FeePropertyColumns.CURRENCY.value: asset,
                octobot_trading.enums.FeePropertyColumns.COST.value: decimal.Decimal(0),
                octobot_trading.enums.FeePropertyColumns.RATE.value: decimal.Decimal(0),
            },
        )
        self.logger.info(f"Deposited {amount} {asset} on {self._trader.exchange_manager.exchange_name} portfolio")

    def _get_total_withdrawals_to_address(self, asset: str, to_address: str) -> decimal.Decimal:
        return sum( # type: ignore
            transaction.quantity
            for transaction in self._trader.exchange_manager.exchange_personal_data.transactions_manager.get_blockchain_transactions(
                blockchain_network=self.blockchain_descriptor.network,
                destination_address=to_address,
                currency=asset,
                transaction_type=octobot_trading.enums.TransactionType.BLOCKCHAIN_WITHDRAWAL,
            )
        )

    def _get_total_deposits_from_address(self, asset: str, from_address: str) -> decimal.Decimal:
        return sum( # type: ignore
            transaction.quantity
            for transaction in self._trader.exchange_manager.exchange_personal_data.transactions_manager.get_blockchain_transactions(
                blockchain_network=self.blockchain_descriptor.network,
                source_address=from_address,
                currency=asset,
                transaction_type=octobot_trading.enums.TransactionType.BLOCKCHAIN_DEPOSIT,
            )
        )
