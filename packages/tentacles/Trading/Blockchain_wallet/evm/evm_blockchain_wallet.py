#  Drakkar-Software OctoBot-Tentacles
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
import contextlib
import dataclasses
import typing
import decimal
import enum
import os
import logging

# Disable web3.py import logging
for logger_name in ["rlp.codec"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
import web3 as web3_lib
import web3.exceptions as web3_exceptions

import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.errors as trading_errors


class EthereumLayer1Network(enum.StrEnum):
    ETHEREUM = "Ethereum Mainnet"


class EthereumLayer2Network(enum.StrEnum):
    POLYGON = "Polygon Mainnet"


class EthereumNativeCurrency(enum.StrEnum):
    ETH = "ETH"  # Ethereum Layer 1 mainnet
    POL = "POL"  # Polygon mainnet (formerly MATIC)


class EthereumDefaultRPCURL(enum.StrEnum):
    ETHEREUM_MAINNET = "https://eth.llamarpc.com"
    POLYGON_MAINNET = "https://polygon-bor-rpc.publicnode.com"


class EVMBlockchainSpecificConfigurationKeys(enum.StrEnum):
    RPC_URL = "rpc_url"


WEI_PER_ETH = decimal.Decimal(10**18)

# Minimal ERC-20 ABI for balanceOf
ERC20_BALANCE_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
        "stateMutability": "view",
    }
]

# Well-known stablecoin token descriptors per network
ETHEREUM_MAINNET_STABLECOINS: list[blockchain_wallets.TokenDescriptor] = [
    blockchain_wallets.TokenDescriptor(
        symbol="USDC",
        decimals=6,
        contract_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    ),
    blockchain_wallets.TokenDescriptor(
        symbol="USDT",
        decimals=6,
        contract_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
    ),
    blockchain_wallets.TokenDescriptor(
        symbol="DAI",
        decimals=18,
        contract_address="0x6B175474E89094C44Da98b954EedeAC495271d0F",
    ),
]

POLYGON_MAINNET_STABLECOINS: list[blockchain_wallets.TokenDescriptor] = [
    blockchain_wallets.TokenDescriptor(
        symbol="USDC",
        decimals=6,
        contract_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    ),
    blockchain_wallets.TokenDescriptor(
        symbol="USDC.e",
        decimals=6,
        contract_address="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    ),
    blockchain_wallets.TokenDescriptor(
        symbol="USDT",
        decimals=6,
        contract_address="0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    ),
    blockchain_wallets.TokenDescriptor(
        symbol="DAI",
        decimals=18,
        contract_address="0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    ),
]


@dataclasses.dataclass
class EVMNetworkConfig:
    network: str
    native_currency: str
    default_rpc_url: str
    well_known_stablecoins: list[blockchain_wallets.TokenDescriptor]


ETHEREUM_MAINNET_CONFIG = EVMNetworkConfig(
    network=EthereumLayer1Network.ETHEREUM,
    native_currency=EthereumNativeCurrency.ETH,
    default_rpc_url=EthereumDefaultRPCURL.ETHEREUM_MAINNET,
    well_known_stablecoins=ETHEREUM_MAINNET_STABLECOINS,
)

POLYGON_MAINNET_CONFIG = EVMNetworkConfig(
    network=EthereumLayer2Network.POLYGON,
    native_currency=EthereumNativeCurrency.POL,
    default_rpc_url=EthereumDefaultRPCURL.POLYGON_MAINNET,
    well_known_stablecoins=POLYGON_MAINNET_STABLECOINS,
)


def converted_web3_error(f):
    async def converted_web3_error_wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except web3_exceptions.Web3Exception as err:
            raise trading_errors.BlockchainWalletCallError(
                f"{err} ({err.__class__.__name__})"
            ) from err
        except Exception as err:
            err_str = str(err).lower()
            if "connect" in err_str or "timeout" in err_str or "connection" in err_str:
                raise trading_errors.BlockchainWalletConnectionError(
                    f"Connection error: {err} ({err.__class__.__name__})"
                ) from err
            raise

    return converted_web3_error_wrapper


class EVMBlockchainWallet(blockchain_wallets.BlockchainWallet):
    BLOCKCHAIN: str = "ethereum"

    def __init__(self, parameters: blockchain_wallets.BlockchainWalletParameters):
        super().__init__(parameters)
        self._w3: typing.Optional[web3_lib.AsyncWeb3] = None
        self._get_rpc_url()  # validate early — raises BlockchainWalletConfigurationError if missing
        self._address: str = self._resolve_address()
        # Disable web3.py logging
        for logger_name in ["web3", "urllib3"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    def _resolve_address(self) -> str:
        descriptor = self.wallet_descriptor
        if descriptor.address:
            return descriptor.address
        if descriptor.private_key:
            return web3_lib.Account.from_key(descriptor.private_key).address
        if descriptor.mnemonic_seed:
            web3_lib.Account.enable_unaudited_hdwallet_features()
            return web3_lib.Account.from_mnemonic(descriptor.mnemonic_seed).address
        raise trading_errors.BlockchainWalletConfigurationError(
            "address, private_key, or mnemonic_seed is required in wallet_descriptor"
        )

    @contextlib.asynccontextmanager
    async def open(self) -> typing.AsyncGenerator["EVMBlockchainWallet", None]:
        rpc_url = self._get_rpc_url()
        provider = web3_lib.AsyncWeb3.AsyncHTTPProvider(rpc_url)
        self._w3 = web3_lib.AsyncWeb3(provider)
        try:
            yield self
        finally:
            self._w3 = None
            await provider.disconnect()

    @property
    def w3(self) -> web3_lib.AsyncWeb3:
        if self._w3 is None:
            raise ValueError(
                "Web3 not initialized, call this function inside the open() context manager"
            )
        return self._w3

    @converted_web3_error
    async def get_native_coin_balance(self) -> blockchain_wallets.Balance:
        address = web3_lib.Web3.to_checksum_address(self._address)
        balance_wei = await self.w3.eth.get_balance(address)
        balance = decimal.Decimal(balance_wei) / WEI_PER_ETH
        return blockchain_wallets.Balance(free=balance)

    @converted_web3_error
    async def get_custom_token_balance(
        self, token_descriptor: blockchain_wallets.TokenDescriptor
    ) -> blockchain_wallets.Balance:
        contract = self.w3.eth.contract(
            address=web3_lib.Web3.to_checksum_address(
                token_descriptor.contract_address
            ),
            abi=ERC20_BALANCE_ABI,
        )
        address = web3_lib.Web3.to_checksum_address(self._address)
        balance_raw = await contract.functions.balanceOf(address).call()
        balance = decimal.Decimal(balance_raw) / decimal.Decimal(
            10**token_descriptor.decimals
        )
        return blockchain_wallets.Balance(free=balance)

    async def transfer_native_coin(
        self, amount: decimal.Decimal, to_address: str
    ) -> blockchain_wallets.Transaction:
        """
        Transfer native coin (ETH, POL) to an address.
        TODO: Implement: build tx dict with to/value/gas, sign with
        self.wallet_descriptor.private_key via w3.eth.account.sign_transaction(),
        send via w3.eth.send_raw_transaction(), return Transaction with tx hash.
        """
        raise NotImplementedError("transfer_native_coin is not yet implemented for EVM")

    async def transfer_custom_token(
        self,
        token_descriptor: blockchain_wallets.TokenDescriptor,
        amount: decimal.Decimal,
        to_address: str,
    ) -> blockchain_wallets.Transaction:
        """
        Transfer an ERC-20 token to an address.
        TODO: Implement: create contract instance with ERC20 transfer ABI,
        encode transfer(to, amount) call, build tx, sign, send, return Transaction.
        """
        raise NotImplementedError(
            "transfer_custom_token is not yet implemented for EVM"
        )

    @converted_web3_error
    async def build_and_send_contract_tx(
        self,
        contract_address: str,
        abi: list,
        function_name: str,
        *args,
        value: int = 0,
        gas_limit: typing.Optional[int] = None,
    ) -> str:
        """
        Build, sign and send a contract write transaction. Returns tx hash.
        TODO: Implement the following steps:
        1. contract = self.w3.eth.contract(
               address=Web3.to_checksum_address(contract_address), abi=abi)
        2. tx_func = getattr(contract.functions, function_name)(*args)
        3. nonce = await self.get_nonce()
        4. gas = gas_limit or await tx_func.estimate_gas(
               {"from": self._address, "value": value})
        5. tx = await tx_func.build_transaction({
               "from": self._address, "nonce": nonce,
               "gas": gas, "value": value})
        6. signed = self.w3.eth.account.sign_transaction(
               tx, self.wallet_descriptor.private_key)
        7. tx_hash = await self.w3.eth.send_raw_transaction(
               signed.raw_transaction)
        8. return tx_hash.hex()
        """
        raise NotImplementedError(
            "build_and_send_contract_tx is not yet implemented for EVM"
        )

    @converted_web3_error
    async def estimate_gas(self, tx_params: dict) -> int:
        """
        Estimate gas for a transaction.
        TODO: Implement via:
        return await self.w3.eth.estimate_gas(tx_params)
        """
        raise NotImplementedError("estimate_gas is not yet implemented for EVM")

    @converted_web3_error
    async def get_nonce(self) -> int:
        """
        Get current transaction count/nonce for the wallet address.
        TODO: Implement via:
        address = Web3.to_checksum_address(self._address)
        return await self.w3.eth.get_transaction_count(address)
        """
        raise NotImplementedError("get_nonce is not yet implemented for EVM")

    @converted_web3_error
    async def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> dict:
        """
        Wait for transaction confirmation and return receipt.
        TODO: Implement via:
        return await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout)
        """
        raise NotImplementedError("wait_for_receipt is not yet implemented for EVM")

    @converted_web3_error
    async def call_contract_function(
        self, contract_address: str, abi: list, function_name: str, *args
    ):
        """
        Execute a read-only contract call (eth_call). Returns decoded result.
        TODO: Implement via:
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi)
        return await getattr(contract.functions, function_name)(*args).call()
        """
        raise NotImplementedError(
            "call_contract_function is not yet implemented for EVM"
        )

    @staticmethod
    def create_blockchain_descriptor_specific_config(**kwargs) -> dict:
        keys = [key.value for key in EVMBlockchainSpecificConfigurationKeys]
        default_config = {
            key: value
            for key in keys
            if (value := os.getenv(f"EVM_{key.upper()}", None)) is not None
        }
        return {**default_config, **{k: v for k, v in kwargs.items() if k in keys}}

    @staticmethod
    def create_wallet_descriptor_specific_config(**kwargs) -> dict:
        return {}

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        pass

    def _get_rpc_url(self) -> str:
        if self.blockchain_descriptor.specific_config:
            if rpc_url := self.blockchain_descriptor.specific_config.get(
                EVMBlockchainSpecificConfigurationKeys.RPC_URL.value
            ):
                return rpc_url
        raise trading_errors.BlockchainWalletConfigurationError(
            f"{EVMBlockchainSpecificConfigurationKeys.RPC_URL.value} is required in "
            f"blockchain_descriptor.specific_config for EVM blockchain wallet. "
            f"ETH mainnet: use {EthereumDefaultRPCURL.ETHEREUM_MAINNET}, "
            f"Polygon mainnet: use {EthereumDefaultRPCURL.POLYGON_MAINNET}."
        )
