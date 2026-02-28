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
import decimal
import os
import mock
import pytest

import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.enums as enums
import octobot_trading.errors as trading_errors
import web3.exceptions as web3_exceptions
import tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet as evm_blockchain_wallet

FAKE_ADDRESS = "0x" + "a" * 40
FAKE_CONTRACT_ADDRESS = "0x" + "b" * 40


def _make_blockchain_config(rpc_url="https://eth.llamarpc.com"):
    return {
        evm_blockchain_wallet.EVMBlockchainSpecificConfigurationKeys.RPC_URL.value: rpc_url,
    }


_SENTINEL = object()  # distinguishes "no config provided" from explicit None


def _make_wallet(
    blockchain_config=_SENTINEL,
    address=FAKE_ADDRESS,
    private_key=None,
    mnemonic_seed=None,
):
    if blockchain_config is _SENTINEL:
        blockchain_config = _make_blockchain_config()
    parameters = blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
            blockchain=evm_blockchain_wallet.EVMBlockchainWallet.BLOCKCHAIN,
            network=evm_blockchain_wallet.EthereumLayer1Network.ETHEREUM,
            native_coin_symbol=evm_blockchain_wallet.EthereumNativeCurrency.ETH,
            specific_config=blockchain_config,
        ),
        wallet_descriptor=blockchain_wallets.WalletDescriptor(
            address=address,
            private_key=private_key,
            mnemonic_seed=mnemonic_seed,
        ),
    )
    return evm_blockchain_wallet.EVMBlockchainWallet(parameters)


@pytest.fixture
def evm_wallet():
    """Factory fixture for EVMBlockchainWallet with valid config."""
    def _create(
        blockchain_config=_SENTINEL,
        address=FAKE_ADDRESS,
        private_key=None,
        mnemonic_seed=None,
    ):
        return _make_wallet(
            blockchain_config=blockchain_config,
            address=address,
            private_key=private_key,
            mnemonic_seed=mnemonic_seed,
        )
    return _create


@pytest.fixture
def mock_web3_module():
    """Patch the entire web3_lib import inside the wallet module."""
    with mock.patch(
        "tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet.web3_lib"
    ) as mock_web3:
        # to_checksum_address is a pure utility: just return the address unchanged
        mock_web3.Web3.to_checksum_address = mock.Mock(side_effect=lambda addr: addr)
        yield mock_web3


@pytest.fixture
def inject_w3():
    """Temporarily set _w3 on a wallet as open() would, then remove it."""
    @contextlib.contextmanager
    def _inject(wallet, mock_w3):
        wallet._w3 = mock_w3
        try:
            yield
        finally:
            del wallet._w3
    return _inject


class TestEnums:
    def test_layer1_network_values(self):
        assert evm_blockchain_wallet.EthereumLayer1Network.ETHEREUM == "Ethereum Mainnet"

    def test_layer2_network_values(self):
        assert evm_blockchain_wallet.EthereumLayer2Network.POLYGON == "Polygon Mainnet"

    def test_native_currency_values(self):
        assert evm_blockchain_wallet.EthereumNativeCurrency.ETH == "ETH"
        assert evm_blockchain_wallet.EthereumNativeCurrency.POL == "POL"

    def test_default_rpc_url_values(self):
        assert "llamarpc" in evm_blockchain_wallet.EthereumDefaultRPCURL.ETHEREUM_MAINNET
        assert "polygon" in evm_blockchain_wallet.EthereumDefaultRPCURL.POLYGON_MAINNET


class TestWellKnownStablecoins:
    def test_ethereum_mainnet_stablecoins_have_expected_symbols(self):
        symbols = {t.symbol for t in evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS}
        assert "USDC" in symbols
        assert "USDT" in symbols
        assert "DAI" in symbols

    def test_polygon_mainnet_stablecoins_have_expected_symbols(self):
        symbols = {t.symbol for t in evm_blockchain_wallet.POLYGON_MAINNET_STABLECOINS}
        assert "USDC" in symbols
        assert "USDC.e" in symbols
        assert "USDT" in symbols
        assert "DAI" in symbols

    def test_ethereum_usdc_has_6_decimals(self):
        usdc = next(
            t for t in evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS if t.symbol == "USDC"
        )
        assert usdc.decimals == 6

    def test_polygon_and_ethereum_usdc_have_different_contract_addresses(self):
        eth_usdc = next(
            t for t in evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS if t.symbol == "USDC"
        )
        pol_usdc = next(
            t for t in evm_blockchain_wallet.POLYGON_MAINNET_STABLECOINS if t.symbol == "USDC"
        )
        assert eth_usdc.contract_address != pol_usdc.contract_address

    def test_dai_has_18_decimals_on_both_networks(self):
        for stablecoins in (
            evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS,
            evm_blockchain_wallet.POLYGON_MAINNET_STABLECOINS,
        ):
            dai = next(t for t in stablecoins if t.symbol == "DAI")
            assert dai.decimals == 18


class TestEVMNetworkConfigs:
    def test_ethereum_mainnet_config(self):
        cfg = evm_blockchain_wallet.ETHEREUM_MAINNET_CONFIG
        assert cfg.network == evm_blockchain_wallet.EthereumLayer1Network.ETHEREUM
        assert cfg.native_currency == evm_blockchain_wallet.EthereumNativeCurrency.ETH
        assert cfg.default_rpc_url == evm_blockchain_wallet.EthereumDefaultRPCURL.ETHEREUM_MAINNET
        assert cfg.well_known_stablecoins is evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS

    def test_polygon_mainnet_config(self):
        cfg = evm_blockchain_wallet.POLYGON_MAINNET_CONFIG
        assert cfg.network == evm_blockchain_wallet.EthereumLayer2Network.POLYGON
        assert cfg.native_currency == evm_blockchain_wallet.EthereumNativeCurrency.POL
        assert cfg.default_rpc_url == evm_blockchain_wallet.EthereumDefaultRPCURL.POLYGON_MAINNET
        assert cfg.well_known_stablecoins is evm_blockchain_wallet.POLYGON_MAINNET_STABLECOINS



class TestGetRpcUrl:
    def test_returns_rpc_url_from_config(self, evm_wallet):
        url = "https://custom-rpc.example.com"
        wallet = evm_wallet(blockchain_config=_make_blockchain_config(rpc_url=url))
        assert wallet._get_rpc_url() == url

    def test_raises_when_rpc_url_missing_from_specific_config(self):
        with pytest.raises(
            trading_errors.BlockchainWalletConfigurationError,
            match="rpc_url",
        ):
            _make_wallet(blockchain_config={})

    def test_raises_when_specific_config_is_none(self):
        with pytest.raises(trading_errors.BlockchainWalletConfigurationError, match="rpc_url"):
            _make_wallet(blockchain_config=None)


class TestW3Property:
    def test_raises_when_not_initialized(self, evm_wallet):
        wallet = evm_wallet()
        with pytest.raises(ValueError, match="Web3 not initialized"):
            _ = wallet.w3


def _make_async_web3_mock(mock_web3_module, w3_instance=None, provider=None):
    """Configure mock_web3_module.AsyncWeb3 for open() without context manager semantics."""
    if w3_instance is None:
        w3_instance = mock.MagicMock()
    if provider is None:
        provider = mock.MagicMock()
    provider.disconnect = mock.AsyncMock(return_value=None)
    mock_web3_module.AsyncWeb3.AsyncHTTPProvider.return_value = provider
    mock_web3_module.AsyncWeb3.return_value = w3_instance
    return w3_instance, provider


class TestOpen:
    @pytest.mark.asyncio
    async def test_sets_w3_inside_context_and_clears_after(
        self, evm_wallet, mock_web3_module
    ):
        wallet = evm_wallet()
        mock_w3_instance, _ = _make_async_web3_mock(mock_web3_module)

        with pytest.raises(ValueError, match="Web3 not initialized"):
            _ = wallet.w3  # not open yet
        async with wallet.open() as opened:
            assert opened.w3 is mock_w3_instance
        with pytest.raises(ValueError, match="Web3 not initialized"):
            _ = wallet.w3  # context has been exited

    @pytest.mark.asyncio
    async def test_open_calls_async_web3_with_rpc_url(self, evm_wallet, mock_web3_module):
        rpc_url = "https://eth.llamarpc.com"
        wallet = evm_wallet(blockchain_config=_make_blockchain_config(rpc_url=rpc_url))
        mock_provider = mock.MagicMock()
        _, mock_provider = _make_async_web3_mock(mock_web3_module, provider=mock_provider)

        async with wallet.open():
            pass

        mock_web3_module.AsyncWeb3.AsyncHTTPProvider.assert_called_once_with(rpc_url)
        mock_web3_module.AsyncWeb3.assert_called_once_with(mock_provider)
        mock_provider.disconnect.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_w3_unavailable_after_inner_block_raises(
        self, evm_wallet, mock_web3_module
    ):
        wallet = evm_wallet()
        _make_async_web3_mock(mock_web3_module)

        with pytest.raises(RuntimeError, match="boom"):
            async with wallet.open():
                raise RuntimeError("boom")

        with pytest.raises(ValueError, match="Web3 not initialized"):
            _ = wallet.w3

    @pytest.mark.asyncio
    async def test_raises_configuration_error_when_rpc_url_missing(self, evm_wallet):
        wallet = evm_wallet()
        with mock.patch.object(
            wallet, "_get_rpc_url", side_effect=trading_errors.BlockchainWalletConfigurationError("rpc_url required")
        ):
            with pytest.raises(trading_errors.BlockchainWalletConfigurationError, match="rpc_url required"):
                async with wallet.open():
                    pass


class TestGetNativeCoinBalance:
    @pytest.mark.asyncio
    async def test_returns_balance_in_eth(self, evm_wallet, mock_web3_module, inject_w3):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(
            return_value=2_000_000_000_000_000_000  # 2 ETH in wei
        )
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("2")
        assert balance.used == decimal.Decimal("0")
        assert balance.total == decimal.Decimal("2")

    @pytest.mark.asyncio
    async def test_returns_zero_balance(self, evm_wallet, mock_web3_module, inject_w3):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(return_value=0)
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("0")
        assert balance.total == decimal.Decimal("0")

    @pytest.mark.asyncio
    async def test_returns_fractional_balance(self, evm_wallet, mock_web3_module, inject_w3):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(
            return_value=500_000_000_000_000_000  # 0.5 ETH
        )
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("0.5")

    @pytest.mark.asyncio
    async def test_calls_get_balance_with_checksum_address(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        address = FAKE_ADDRESS
        wallet = evm_wallet(address=address)
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(return_value=0)
        with inject_w3(wallet, mock_w3):
            await wallet.get_native_coin_balance()

        mock_web3_module.Web3.to_checksum_address.assert_called_with(address)
        mock_w3.eth.get_balance.assert_awaited_once_with(address)

    @pytest.mark.asyncio
    async def test_web3_exception_converted_to_call_error(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(
            side_effect=web3_exceptions.Web3Exception("node error")
        )
        with inject_w3(wallet, mock_w3):
            with pytest.raises(trading_errors.BlockchainWalletCallError, match="node error"):
                await wallet.get_native_coin_balance()

    @pytest.mark.asyncio
    async def test_connection_error_converted_to_connection_error(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(
            side_effect=Exception("Connection refused")
        )
        with inject_w3(wallet, mock_w3):
            with pytest.raises(trading_errors.BlockchainWalletConnectionError):
                await wallet.get_native_coin_balance()

    @pytest.mark.asyncio
    async def test_timeout_error_converted_to_connection_error(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(
            side_effect=Exception("request timeout after 30s")
        )
        with inject_w3(wallet, mock_w3):
            with pytest.raises(trading_errors.BlockchainWalletConnectionError):
                await wallet.get_native_coin_balance()


class TestGetCustomTokenBalance:
    def _make_token(self, symbol="USDC", decimals=6, contract=FAKE_CONTRACT_ADDRESS):
        return blockchain_wallets.TokenDescriptor(
            symbol=symbol,
            decimals=decimals,
            contract_address=contract,
        )

    def _make_mock_contract(self, raw_balance: int):
        mock_contract = mock.MagicMock()
        mock_contract.functions.balanceOf.return_value.call = mock.AsyncMock(
            return_value=raw_balance
        )
        return mock_contract

    @pytest.mark.asyncio
    async def test_returns_erc20_balance_with_correct_decimals(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.contract.return_value = self._make_mock_contract(1_000_000)  # 1 USDC
        token = self._make_token(symbol="USDC", decimals=6)
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_custom_token_balance(token)

        assert balance.free == decimal.Decimal("1")
        assert balance.used == decimal.Decimal("0")
        assert balance.total == decimal.Decimal("1")

    @pytest.mark.asyncio
    async def test_returns_zero_token_balance(self, evm_wallet, mock_web3_module, inject_w3):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_w3.eth.contract.return_value = self._make_mock_contract(0)
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_custom_token_balance(self._make_token())

        assert balance.free == decimal.Decimal("0")

    @pytest.mark.asyncio
    async def test_18_decimal_token_balance(self, evm_wallet, mock_web3_module, inject_w3):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        # 2.5 DAI = 2_500_000_000_000_000_000 (18 decimals)
        mock_w3.eth.contract.return_value = self._make_mock_contract(2_500_000_000_000_000_000)
        token = self._make_token(symbol="DAI", decimals=18)
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_custom_token_balance(token)

        assert balance.free == decimal.Decimal("2.5")

    @pytest.mark.asyncio
    async def test_creates_contract_with_checksum_addresses(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet(address=FAKE_ADDRESS)
        mock_w3 = mock.MagicMock()
        mock_w3.eth.contract.return_value = self._make_mock_contract(0)
        token = self._make_token(contract=FAKE_CONTRACT_ADDRESS)
        with inject_w3(wallet, mock_w3):
            await wallet.get_custom_token_balance(token)

        mock_web3_module.Web3.to_checksum_address.assert_any_call(FAKE_CONTRACT_ADDRESS)
        mock_web3_module.Web3.to_checksum_address.assert_any_call(FAKE_ADDRESS)
        mock_w3.eth.contract.assert_called_once_with(
            address=FAKE_CONTRACT_ADDRESS,
            abi=evm_blockchain_wallet.ERC20_BALANCE_ABI,
        )

    @pytest.mark.asyncio
    async def test_calls_balance_of_with_wallet_address(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet(address=FAKE_ADDRESS)
        mock_contract = self._make_mock_contract(500_000)
        mock_w3 = mock.MagicMock()
        mock_w3.eth.contract.return_value = mock_contract
        with inject_w3(wallet, mock_w3):
            await wallet.get_custom_token_balance(self._make_token())

        mock_contract.functions.balanceOf.assert_called_once_with(FAKE_ADDRESS)

    @pytest.mark.asyncio
    async def test_web3_exception_converted_to_call_error(
        self, evm_wallet, mock_web3_module, inject_w3
    ):
        wallet = evm_wallet()
        mock_w3 = mock.MagicMock()
        mock_contract = mock.MagicMock()
        mock_contract.functions.balanceOf.return_value.call = mock.AsyncMock(
            side_effect=web3_exceptions.Web3Exception("contract call failed")
        )
        mock_w3.eth.contract.return_value = mock_contract
        with inject_w3(wallet, mock_w3):
            with pytest.raises(trading_errors.BlockchainWalletCallError, match="contract call failed"):
                await wallet.get_custom_token_balance(self._make_token())


class TestGetDepositAddress:
    @pytest.mark.asyncio
    async def test_returns_wallet_address(self, evm_wallet):
        wallet = evm_wallet(address=FAKE_ADDRESS)
        result = await wallet.get_deposit_address(asset="ETH")
        assert result[enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value] == FAKE_ADDRESS
        assert result[enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value] == "ETH"
        assert result[enums.ExchangeConstantsDepositAddressColumns.NETWORK.value] == (
            evm_blockchain_wallet.EthereumLayer1Network.ETHEREUM
        )


class TestCreateBlockchainDescriptorSpecificConfig:
    def test_returns_rpc_url_from_kwargs(self):
        config = evm_blockchain_wallet.EVMBlockchainWallet.create_blockchain_descriptor_specific_config(
            rpc_url="https://custom.example.com"
        )
        assert config["rpc_url"] == "https://custom.example.com"

    def test_ignores_unknown_keys(self):
        config = evm_blockchain_wallet.EVMBlockchainWallet.create_blockchain_descriptor_specific_config(
            rpc_url="https://custom.example.com",
            unknown_key="ignored",
        )
        assert "unknown_key" not in config

    def test_reads_from_env_var(self, monkeypatch):
        monkeypatch.setenv("EVM_RPC_URL", "https://from-env.example.com")
        config = evm_blockchain_wallet.EVMBlockchainWallet.create_blockchain_descriptor_specific_config()
        assert config["rpc_url"] == "https://from-env.example.com"

    def test_kwarg_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("EVM_RPC_URL", "https://from-env.example.com")
        config = evm_blockchain_wallet.EVMBlockchainWallet.create_blockchain_descriptor_specific_config(
            rpc_url="https://explicit.example.com"
        )
        assert config["rpc_url"] == "https://explicit.example.com"


FAKE_PRIVATE_KEY = "0x" + "f" * 64
FAKE_MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
DERIVED_ADDRESS_FROM_KEY = "0x" + "d" * 40
DERIVED_ADDRESS_FROM_MNEMONIC = "0x" + "e" * 40


class TestWalletInitialization:
    def test_address_only_is_used_directly(self, evm_wallet):
        """Public address alone is sufficient — no private key needed for read-only ops."""
        wallet = evm_wallet(address=FAKE_ADDRESS)
        assert wallet._address == FAKE_ADDRESS

    def test_private_key_derives_address(self):
        """When only a private key is supplied the address is derived from it."""
        with mock.patch(
            "tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet.web3_lib"
        ) as mock_web3:
            mock_web3.Account.from_key.return_value.address = DERIVED_ADDRESS_FROM_KEY
            wallet = _make_wallet(address=None, private_key=FAKE_PRIVATE_KEY)

        assert wallet._address == DERIVED_ADDRESS_FROM_KEY
        mock_web3.Account.from_key.assert_called_once_with(FAKE_PRIVATE_KEY)

    def test_mnemonic_seed_derives_address(self):
        """When only a mnemonic seed is supplied the address is derived from it."""
        with mock.patch(
            "tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet.web3_lib"
        ) as mock_web3:
            mock_web3.Account.from_mnemonic.return_value.address = DERIVED_ADDRESS_FROM_MNEMONIC
            wallet = _make_wallet(address=None, mnemonic_seed=FAKE_MNEMONIC)

        assert wallet._address == DERIVED_ADDRESS_FROM_MNEMONIC
        mock_web3.Account.enable_unaudited_hdwallet_features.assert_called_once()
        mock_web3.Account.from_mnemonic.assert_called_once_with(FAKE_MNEMONIC)

    def test_address_takes_priority_over_private_key(self):
        """Explicit address wins even when a private key is also provided."""
        with mock.patch(
            "tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet.web3_lib"
        ) as mock_web3:
            wallet = _make_wallet(address=FAKE_ADDRESS, private_key=FAKE_PRIVATE_KEY)

        assert wallet._address == FAKE_ADDRESS
        mock_web3.Account.from_key.assert_not_called()

    def test_address_takes_priority_over_mnemonic(self):
        """Explicit address wins even when a mnemonic is also provided."""
        with mock.patch(
            "tentacles.Trading.Blockchain_wallet.evm.evm_blockchain_wallet.web3_lib"
        ) as mock_web3:
            wallet = _make_wallet(address=FAKE_ADDRESS, mnemonic_seed=FAKE_MNEMONIC)

        assert wallet._address == FAKE_ADDRESS
        mock_web3.Account.from_mnemonic.assert_not_called()

    def test_no_credentials_raises_configuration_error(self):
        """No address, private_key, or mnemonic_seed → BlockchainWalletConfigurationError."""
        with pytest.raises(
            trading_errors.BlockchainWalletConfigurationError,
            match="address",
        ):
            _make_wallet(address=None, private_key=None, mnemonic_seed=None)


# ---------------------------------------------------------------------------
# Balance fetching with a public address only (read-only / watch-only wallet)
# ---------------------------------------------------------------------------


class TestGetNativeCoinBalancePublicKeyOnly:
    """
    Explicit tests showing that balance queries work with a public address alone.
    No private key or mnemonic is required for read-only operations.
    """

    @pytest.mark.asyncio
    async def test_native_balance_with_address_only(self, evm_wallet, mock_web3_module, inject_w3):
        """Fetch ETH balance using only a public address."""
        wallet = evm_wallet(address=FAKE_ADDRESS)  # no private_key, no mnemonic_seed
        assert wallet._address == FAKE_ADDRESS

        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(return_value=3_000_000_000_000_000_000)  # 3 ETH
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("3")
        mock_w3.eth.get_balance.assert_awaited_once_with(FAKE_ADDRESS)

    @pytest.mark.asyncio
    async def test_token_balance_with_address_only(self, evm_wallet, mock_web3_module, inject_w3):
        """Fetch ERC-20 token balance using only a public address."""
        wallet = evm_wallet(address=FAKE_ADDRESS)  # no private_key, no mnemonic_seed
        token = blockchain_wallets.TokenDescriptor(
            symbol="USDC", decimals=6, contract_address=FAKE_CONTRACT_ADDRESS
        )
        mock_contract = mock.MagicMock()
        mock_contract.functions.balanceOf.return_value.call = mock.AsyncMock(
            return_value=5_000_000  # 5 USDC
        )
        mock_w3 = mock.MagicMock()
        mock_w3.eth.contract.return_value = mock_contract
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_custom_token_balance(token)

        assert balance.free == decimal.Decimal("5")

    @pytest.mark.asyncio
    async def test_balance_uses_derived_address_from_private_key(self, mock_web3_module, inject_w3):
        """After init from private key, balance is fetched against the derived address."""
        mock_web3_module.Account.from_key.return_value.address = DERIVED_ADDRESS_FROM_KEY

        wallet = _make_wallet(address=None, private_key=FAKE_PRIVATE_KEY)
        assert wallet._address == DERIVED_ADDRESS_FROM_KEY

        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(return_value=1_000_000_000_000_000_000)
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("1")
        mock_w3.eth.get_balance.assert_awaited_once_with(DERIVED_ADDRESS_FROM_KEY)

    @pytest.mark.asyncio
    async def test_balance_uses_derived_address_from_mnemonic(self, mock_web3_module, inject_w3):
        """After init from mnemonic, balance is fetched against the derived address."""
        mock_web3_module.Account.from_mnemonic.return_value.address = DERIVED_ADDRESS_FROM_MNEMONIC

        wallet = _make_wallet(address=None, mnemonic_seed=FAKE_MNEMONIC)
        assert wallet._address == DERIVED_ADDRESS_FROM_MNEMONIC

        mock_w3 = mock.MagicMock()
        mock_w3.eth.get_balance = mock.AsyncMock(return_value=500_000_000_000_000_000)  # 0.5 ETH
        with inject_w3(wallet, mock_w3):
            balance = await wallet.get_native_coin_balance()

        assert balance.free == decimal.Decimal("0.5")
        mock_w3.eth.get_balance.assert_awaited_once_with(DERIVED_ADDRESS_FROM_MNEMONIC)



_ETH_TEST_ADDRESS = os.getenv("TEST_EVM_ETH_ADDRESS")
_POLYGON_TEST_ADDRESS = os.getenv("TEST_EVM_POLYGON_ADDRESS")


def _make_live_wallet(network_config, address):
    parameters = blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
            blockchain=evm_blockchain_wallet.EVMBlockchainWallet.BLOCKCHAIN,
            network=network_config.network,
            native_coin_symbol=network_config.native_currency,
            specific_config={
                evm_blockchain_wallet.EVMBlockchainSpecificConfigurationKeys.RPC_URL.value: network_config.default_rpc_url
            },
            tokens=network_config.well_known_stablecoins,
        ),
        wallet_descriptor=blockchain_wallets.WalletDescriptor(address=address),
    )
    return evm_blockchain_wallet.EVMBlockchainWallet(parameters)


class TestLiveEthereumBalance:
    @pytest.mark.asyncio
    @pytest.mark.skipif(not _ETH_TEST_ADDRESS, reason="TEST_EVM_ETH_ADDRESS not set")
    async def test_fetch_eth_native_balance(self):
        wallet = _make_live_wallet(evm_blockchain_wallet.ETHEREUM_MAINNET_CONFIG, _ETH_TEST_ADDRESS)
        async with wallet.open():
            balance = await wallet.get_native_coin_balance()
        print(f"\nETH balance for {_ETH_TEST_ADDRESS}: {balance.free} ETH")
        assert balance.free >= decimal.Decimal("0")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _ETH_TEST_ADDRESS, reason="TEST_EVM_ETH_ADDRESS not set")
    async def test_fetch_eth_stablecoin_balances(self):
        wallet = _make_live_wallet(evm_blockchain_wallet.ETHEREUM_MAINNET_CONFIG, _ETH_TEST_ADDRESS)
        async with wallet.open():
            for token in evm_blockchain_wallet.ETHEREUM_MAINNET_STABLECOINS:
                balance = await wallet.get_custom_token_balance(token)
                print(f"\n  {token.symbol} ({token.contract_address}): {balance.free}")
                assert balance.free >= decimal.Decimal("0"), f"{token.symbol} balance is negative"


class TestLivePolygonBalance:
    @pytest.mark.asyncio
    @pytest.mark.skipif(not _POLYGON_TEST_ADDRESS, reason="TEST_EVM_POLYGON_ADDRESS not set")
    async def test_fetch_polygon_native_balance(self):
        wallet = _make_live_wallet(evm_blockchain_wallet.POLYGON_MAINNET_CONFIG, _POLYGON_TEST_ADDRESS)
        async with wallet.open():
            balance = await wallet.get_native_coin_balance()
        print(f"\nPOL balance for {_POLYGON_TEST_ADDRESS}: {balance.free} POL")
        assert balance.free >= decimal.Decimal("0")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _POLYGON_TEST_ADDRESS, reason="TEST_EVM_POLYGON_ADDRESS not set")
    async def test_fetch_polygon_stablecoin_balances(self):
        wallet = _make_live_wallet(evm_blockchain_wallet.POLYGON_MAINNET_CONFIG, _POLYGON_TEST_ADDRESS)
        async with wallet.open():
            for token in evm_blockchain_wallet.POLYGON_MAINNET_STABLECOINS:
                balance = await wallet.get_custom_token_balance(token)
                print(f"\n  {token.symbol} ({token.contract_address}): {balance.free}")
                assert balance.free >= decimal.Decimal("0"), f"{token.symbol} balance is negative"
