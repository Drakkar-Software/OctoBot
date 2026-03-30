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

import decimal

import pytest

import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.errors as trading_errors
import tentacles.Trading.Blockchain_wallet.bitcoin.bitcoin_blockchain_wallet as bitcoin_blockchain_wallet


pytestmark = pytest.mark.asyncio

BINANCE_COLD_WALLET_ADDRESS = "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"
FALSE_BTC_ADDRESS = "17ouWjN7nvPWkZKo2svTF81etXL6Qxnty7"


def _make_bitcoin_wallet(address: str) -> bitcoin_blockchain_wallet.BitcoinBlockchainWallet:
    parameters = blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
            blockchain=bitcoin_blockchain_wallet.BitcoinBlockchainWallet.BLOCKCHAIN,
            network="Bitcoin",
            native_coin_symbol="BTC",
            specific_config={},
        ),
        wallet_descriptor=blockchain_wallets.WalletDescriptor(address=address),
    )
    return bitcoin_blockchain_wallet.BitcoinBlockchainWallet(parameters)


async def test_get_native_coin_balance_binance_cold_wallet_positive():
    wallet = _make_bitcoin_wallet(BINANCE_COLD_WALLET_ADDRESS)
    async with wallet.open():
        balance = await wallet.get_native_coin_balance()
    assert balance.free > decimal.Decimal(0)


async def test_get_native_coin_balance_false_address_zero():
    wallet = _make_bitcoin_wallet(FALSE_BTC_ADDRESS)
    async with wallet.open():
        balance = await wallet.get_native_coin_balance()
    assert balance.free == decimal.Decimal(0)


def test_resolve_address_requires_wallet_address():
    parameters = blockchain_wallets.BlockchainWalletParameters(
        blockchain_descriptor=blockchain_wallets.BlockchainDescriptor(
            blockchain=bitcoin_blockchain_wallet.BitcoinBlockchainWallet.BLOCKCHAIN,
            network="Bitcoin",
            native_coin_symbol="BTC",
            specific_config={},
        ),
        wallet_descriptor=blockchain_wallets.WalletDescriptor(address=None),
    )
    wallet = bitcoin_blockchain_wallet.BitcoinBlockchainWallet(parameters)
    with pytest.raises(NotImplementedError):
        wallet._resolve_address()


async def test_get_native_coin_balance_without_open_raises():
    wallet = _make_bitcoin_wallet(BINANCE_COLD_WALLET_ADDRESS)
    with pytest.raises(trading_errors.BlockchainWalletCallError):
        await wallet.get_native_coin_balance()


async def test_transfer_native_coin_not_implemented():
    wallet = _make_bitcoin_wallet(BINANCE_COLD_WALLET_ADDRESS)
    with pytest.raises(NotImplementedError):
        await wallet.transfer_native_coin(decimal.Decimal("1"), BINANCE_COLD_WALLET_ADDRESS)
