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

"""
Aave V3 contract addresses on Polygon mainnet.
Source: https://docs.aave.com/developers/deployed-contracts/v3-mainnet/polygon
"""

POLYGON_CHAIN_ID = 137

# Core protocol contracts
AAVE_V3_POOL_ADDRESS = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
AAVE_V3_POOL_DATA_PROVIDER_ADDRESS = "0x69FA688f1Dc47d4B5d8029D5a35FB7a548310654"
AAVE_V3_ORACLE_ADDRESS = "0xb023e699F5a33916Ea823A16485e259257cA8Bd1"
AAVE_V3_POOL_ADDRESSES_PROVIDER = "0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb"

# Common token addresses on Polygon mainnet
POLYGON_TOKEN_ADDRESSES = {
    "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "USDC.e": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    "AAVE": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",
}

# Token decimals
POLYGON_TOKEN_DECIMALS = {
    "USDC": 6,
    "USDC.e": 6,
    "USDT": 6,
    "DAI": 18,
    "WETH": 18,
    "WMATIC": 18,
    "WBTC": 8,
    "AAVE": 18,
}

# Aave V3 constants
HEALTH_FACTOR_DECIMALS = 18  # healthFactor from getUserAccountData has 18 decimals
BASE_CURRENCY_DECIMALS = 8  # USD values from getUserAccountData have 8 decimals
DEFAULT_CLOSE_FACTOR = 50  # 50% - max portion of debt liquidatable per call (in percent)
LIQUIDATION_BONUS_BASE = 10000  # basis points (10000 = 100%)
