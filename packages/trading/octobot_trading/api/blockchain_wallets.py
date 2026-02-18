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
import contextlib

import octobot_trading.blockchain_wallets as blockchain_wallets

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


@contextlib.asynccontextmanager
async def blockchain_wallet_context(
    parameters: blockchain_wallets.BlockchainWalletParameters,
    trader: "octobot_trading.exchanges.Trader"
) -> typing.AsyncGenerator[blockchain_wallets.BlockchainWallet, None]:
    wallet = blockchain_wallets.create_blockchain_wallet(parameters, trader)
    async with wallet.open() as wallet:
        yield wallet
