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

import typing
import decimal
import contextlib

import aiohttp

import octobot_trading.blockchain_wallets as blockchain_wallets
import octobot_trading.errors as trading_errors

BLOCKSTREAM_INFO_API_BASE = "https://blockstream.info/api"
_SATOSHIS_PER_BTC = decimal.Decimal(100_000_000)


def _net_balance_satoshis_from_stats(stats: dict) -> decimal.Decimal:
    if not stats:
        return decimal.Decimal(0)
    funded = decimal.Decimal(stats.get("funded_txo_sum") or 0)
    spent = decimal.Decimal(stats.get("spent_txo_sum") or 0)
    return funded - spent


class BitcoinBlockchainWallet(blockchain_wallets.BlockchainWallet):
    BLOCKCHAIN: str = "bitcoin"

    def __init__(self, parameters: blockchain_wallets.BlockchainWalletParameters):
        super().__init__(parameters)
        self._session: typing.Optional[aiohttp.ClientSession] = None

    def _resolve_address(self) -> str:
        descriptor = self.wallet_descriptor
        if descriptor.address:
            return descriptor.address
        raise NotImplementedError("address is required in wallet_descriptor")

    @contextlib.asynccontextmanager
    async def open(self) -> typing.AsyncGenerator["BitcoinBlockchainWallet", None]:
        self._session = aiohttp.ClientSession()
        try:
            yield self
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None

    async def get_native_coin_balance(self) -> blockchain_wallets.Balance:
        if self._session is None:
            raise trading_errors.BlockchainWalletCallError(
                "Bitcoin wallet HTTP session is not open; use `async with wallet.open()`"
            )
        address = self._resolve_address()
        url = f"{BLOCKSTREAM_INFO_API_BASE}/address/{address}"
        async with self._session.get(url) as response:
            if response.status != 200:
                detail = (await response.text())[:500]
                raise trading_errors.BlockchainWalletCallError(
                    f"Blockstream address API HTTP {response.status}: {detail}"
                )
            payload = await response.json()
        satoshis = (
            _net_balance_satoshis_from_stats(payload.get("chain_stats") or {})
            + _net_balance_satoshis_from_stats(payload.get("mempool_stats") or {})
        )
        balance_btc = satoshis / _SATOSHIS_PER_BTC
        return blockchain_wallets.Balance(free=balance_btc)

    async def transfer_native_coin(
        self, amount: decimal.Decimal, to_address: str
    ) -> blockchain_wallets.Transaction:
        raise NotImplementedError("transfer_native_coin is not yet implemented for EVM")
