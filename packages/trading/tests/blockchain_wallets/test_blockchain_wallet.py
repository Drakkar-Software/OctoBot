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

import octobot_trading.blockchain_wallets
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
from tests.blockchain_wallets import blockchain_descriptor_simulated, wallet_descriptor


NATIVE_COIN_TRANSACTION_ID = "test_tx_id_native_coin"
CUSTOM_TOKEN_TRANSACTION_ID = "test_tx_id_custom_token"


class BlockchainTestWallet(octobot_trading.blockchain_wallets.BlockchainWallet):
    """Concrete implementation for testing"""
    BLOCKCHAIN = "ethereum"
    
    async def get_native_coin_balance(self):
        return octobot_trading.blockchain_wallets.Balance(free=decimal.Decimal("10"))
    
    async def get_custom_token_balance(self, token_descriptor):
        return octobot_trading.blockchain_wallets.Balance(free=decimal.Decimal("5"))
    
    async def transfer_native_coin(self, amount, to_address):
        return octobot_trading.blockchain_wallets.Transaction(
            txid=NATIVE_COIN_TRANSACTION_ID,
            timestamp=1234567890,
            address_from=self.wallet_descriptor.address,
            address_to=to_address,
            amount=amount,
            currency=self.blockchain_descriptor.native_coin_symbol,
            network=self.blockchain_descriptor.network
        )
    
    async def transfer_custom_token(self, token_descriptor, amount, to_address):
        return octobot_trading.blockchain_wallets.Transaction(
            txid=CUSTOM_TOKEN_TRANSACTION_ID,
            timestamp=1234567890,
            address_from=self.wallet_descriptor.address,
            address_to=to_address,
            amount=amount,
            currency=token_descriptor.symbol,
            network=self.blockchain_descriptor.network
        )


@pytest.fixture
def test_wallet(blockchain_descriptor_simulated, wallet_descriptor):
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_simulated,
        wallet_descriptor=wallet_descriptor
    )
    return BlockchainTestWallet(parameters)


@pytest.fixture
def blockchain_descriptor_with_tokens():
    token = octobot_trading.blockchain_wallets.TokenDescriptor(
        symbol="USDT",
        decimals=18,
        contract_address="0x1234567890123456789012345678901234567890"
    )
    return octobot_trading.blockchain_wallets.BlockchainDescriptor(
        blockchain=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.BLOCKCHAIN,
        network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
        native_coin_symbol="ETH",
        tokens=[token]
    )


@pytest.fixture
def test_wallet_with_tokens(blockchain_descriptor_with_tokens, wallet_descriptor):
    parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_descriptor_with_tokens,
        wallet_descriptor=wallet_descriptor
    )
    return BlockchainTestWallet(parameters)


class TestGetBalance:
    @pytest.mark.asyncio
    async def test_native_coin_only(self, test_wallet):
        balance = await test_wallet.get_balance()
        assert balance == {
            "ETH": {
                constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("10"),
                constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("10"),
                constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("0"),
            }
        }

    @pytest.mark.asyncio
    async def test_with_tokens(self, test_wallet_with_tokens):
        balance = await test_wallet_with_tokens.get_balance()
        assert balance == {
            "ETH": {
                constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("10"),
                constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("10"),
                constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("0"),
            },
            "USDT": {
                constants.CONFIG_PORTFOLIO_FREE: decimal.Decimal("5"),
                constants.CONFIG_PORTFOLIO_TOTAL: decimal.Decimal("5"),
                constants.CONFIG_PORTFOLIO_USED: decimal.Decimal("0"),
            }
        }

    @pytest.mark.asyncio
    async def test_no_native_coin(self):
        blockchain_descriptor = octobot_trading.blockchain_wallets.BlockchainDescriptor(
            blockchain=octobot_trading.blockchain_wallets.BlockchainWalletSimulator.BLOCKCHAIN,
            network=constants.SIMULATED_BLOCKCHAIN_NETWORK,
            native_coin_symbol=None
        )
        wallet_desc = octobot_trading.blockchain_wallets.WalletDescriptor(
            address="0x123",
            private_key="0xabc"
        )
        parameters = octobot_trading.blockchain_wallets.BlockchainWalletParameters(
            blockchain_descriptor=blockchain_descriptor,
            wallet_descriptor=wallet_desc
        )
        wallet = BlockchainTestWallet(parameters)

        balance = await wallet.get_balance()

        # Should be empty if no native coin and no tokens
        assert balance == {}


class TestWithdraw:
    @pytest.mark.asyncio
    async def test_native_coin(self, test_wallet):
        with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True):
            result = await test_wallet.withdraw("ETH", decimal.Decimal("1"), "ethereum", "0xrecipient")

            assert result[enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "ETH"
            assert result[enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("1")
            assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0xrecipient"
            assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value] == test_wallet.wallet_descriptor.address
            assert result[enums.ExchangeConstantsTransactionColumns.TXID.value] == NATIVE_COIN_TRANSACTION_ID
            assert result[enums.ExchangeConstantsTransactionColumns.NETWORK.value] == test_wallet.blockchain_descriptor.network

    @pytest.mark.asyncio
    async def test_custom_token(self, test_wallet_with_tokens):
        with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True):
            result = await test_wallet_with_tokens.withdraw("USDT", decimal.Decimal("2"), "ethereum", "0xrecipient")

            assert result[enums.ExchangeConstantsTransactionColumns.CURRENCY.value] == "USDT"
            assert result[enums.ExchangeConstantsTransactionColumns.AMOUNT.value] == decimal.Decimal("2")
            assert result[enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value] == "0xrecipient"
            assert result[enums.ExchangeConstantsTransactionColumns.TXID.value] == CUSTOM_TOKEN_TRANSACTION_ID
            assert result[enums.ExchangeConstantsTransactionColumns.NETWORK.value] == test_wallet_with_tokens.blockchain_descriptor.network

    @pytest.mark.asyncio
    async def test_disabled(self, test_wallet):
        with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', False), \
            mock.patch.object(test_wallet, 'transfer_native_coin', mock.AsyncMock()) as transfer_native_coin_mock, \
            mock.patch.object(test_wallet, 'transfer_custom_token', mock.AsyncMock()) as transfer_custom_token_mock:
            with pytest.raises(errors.DisabledFundsTransferError, match="Funds transfer is not enabled"):
                await test_wallet.withdraw("ETH", decimal.Decimal("1"), "ethereum", "0xrecipient")
            with pytest.raises(errors.DisabledFundsTransferError, match="Funds transfer is not enabled"):
                await test_wallet.withdraw("USDT", decimal.Decimal("2"), "ethereum", "0xrecipient")
            with pytest.raises(errors.DisabledFundsTransferError, match="Funds transfer is not enabled"):
                await test_wallet.withdraw("INVALID", decimal.Decimal("3"), "ethereum", "0xrecipient")
            # transfer methods should not be called
            transfer_native_coin_mock.assert_not_called()
            transfer_custom_token_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_token(self, test_wallet_with_tokens):
        with mock.patch('octobot_trading.constants.ALLOW_FUNDS_TRANSFER', True):
            with pytest.raises(KeyError, match="Token INVALID not found"):
                await test_wallet_with_tokens.withdraw("INVALID", decimal.Decimal("1"), "ethereum", "0xrecipient")


class TestGetDepositAddress:
    @pytest.mark.asyncio
    async def test_default(self, test_wallet):
        result = await test_wallet.get_deposit_address("ETH")

        assert result[enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value] == "ETH"
        assert result[enums.ExchangeConstantsDepositAddressColumns.NETWORK.value] == test_wallet.blockchain_descriptor.network
        assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == test_wallet.wallet_descriptor.address

    @pytest.mark.asyncio
    async def test_with_params(self, test_wallet):
        params = {"network": "mainnet"}
        result = await test_wallet.get_deposit_address("ETH", params=params)

        # Params are ignored in the base implementation, address is always wallet address
        assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == test_wallet.wallet_descriptor.address


class TestOpen:
    @pytest.mark.asyncio
    async def test_default(self, test_wallet):
        # open does nothing by default
        async with test_wallet.open() as opened_wallet:
            assert opened_wallet is test_wallet


class TestGetProxyConfig:
    def test_returns_blockchain_specific_proxy(self):
        blockchain_env = {
            "ETHEREUM_HTTP_PROXY": "http://ethereum-http",
            "ETHEREUM_HTTPS_PROXY": "https://ethereum-https",
            "ETHEREUM_SOCKS_PROXY": "socks5://ethereum-socks",
            "ETHEREUM_WS_PROXY": "ws://ethereum-ws",
            "ETHEREUM_WSS_PROXY": "wss://ethereum-wss",
            "ETHEREUM_WS_SOCKS_PROXY": "socks5://ethereum-ws-socks",
        }

        with mock.patch.dict("os.environ", blockchain_env, clear=True):
            selected_proxy_config = BlockchainTestWallet.get_proxy_config()

        assert selected_proxy_config.http_proxy == "http://ethereum-http"
        assert selected_proxy_config.https_proxy == "https://ethereum-https"
        assert selected_proxy_config.socks_proxy == "socks5://ethereum-socks"
        assert selected_proxy_config.ws_proxy == "ws://ethereum-ws"
        assert selected_proxy_config.wss_proxy == "wss://ethereum-wss"
        assert selected_proxy_config.ws_socks_proxy == "socks5://ethereum-ws-socks"

    def test_falls_back_to_generic_proxy(self):
        generic_env = {
            "BLOCKCHAIN_HTTP_PROXY": "http://generic-http",
            "BLOCKCHAIN_HTTPS_PROXY": "https://generic-https",
            "BLOCKCHAIN_SOCKS_PROXY": "socks5://generic-socks",
            "BLOCKCHAIN_WS_PROXY": "ws://generic-ws",
            "BLOCKCHAIN_WSS_PROXY": "wss://generic-wss",
            "BLOCKCHAIN_WS_SOCKS_PROXY": "socks5://generic-ws-socks",
        }

        with mock.patch.dict("os.environ", generic_env, clear=True):
            selected_proxy_config = BlockchainTestWallet.get_proxy_config()

        assert selected_proxy_config.http_proxy == "http://generic-http"
        assert selected_proxy_config.https_proxy == "https://generic-https"
        assert selected_proxy_config.socks_proxy == "socks5://generic-socks"
        assert selected_proxy_config.ws_proxy == "ws://generic-ws"
        assert selected_proxy_config.wss_proxy == "wss://generic-wss"
        assert selected_proxy_config.ws_socks_proxy == "socks5://generic-ws-socks"


class TestGetProxyConfigByKey:
    def test_maps_all_proxy_environment_variables(self):
        proxy_env = {
            "CUSTOMKEY_HTTP_PROXY": "http://custom-http",
            "CUSTOMKEY_HTTPS_PROXY": "https://custom-https",
            "CUSTOMKEY_SOCKS_PROXY": "socks5://custom-socks",
            "CUSTOMKEY_WS_PROXY": "ws://custom-ws",
            "CUSTOMKEY_WSS_PROXY": "wss://custom-wss",
            "CUSTOMKEY_WS_SOCKS_PROXY": "socks5://custom-ws-socks",
        }

        with mock.patch.dict("os.environ", proxy_env, clear=True):
            selected_proxy_config = BlockchainTestWallet._get_proxy_config("CUSTOMKEY")

        assert selected_proxy_config.http_proxy == "http://custom-http"
        assert selected_proxy_config.https_proxy == "https://custom-https"
        assert selected_proxy_config.socks_proxy == "socks5://custom-socks"
        assert selected_proxy_config.ws_proxy == "ws://custom-ws"
        assert selected_proxy_config.wss_proxy == "wss://custom-wss"
        assert selected_proxy_config.ws_socks_proxy == "socks5://custom-ws-socks"
