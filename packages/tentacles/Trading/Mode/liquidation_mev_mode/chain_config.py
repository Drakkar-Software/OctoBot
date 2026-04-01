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
import dataclasses


@dataclasses.dataclass(frozen=True)
class ChainConfig:
    chain_id: int
    name: str
    native_token: str
    default_rpc_url: str
    block_time_seconds: float
    explorer_url: str


POLYGON_CONFIG = ChainConfig(
    chain_id=137,
    name="Polygon",
    native_token="POL",
    default_rpc_url="https://polygon-bor-rpc.publicnode.com",
    block_time_seconds=2.0,
    explorer_url="https://polygonscan.com",
)

# TODO: Add additional chain configurations as MEV support expands
# ETHEREUM_CONFIG = ChainConfig(
#     chain_id=1, name="Ethereum", native_token="ETH",
#     default_rpc_url="https://eth.llamarpc.com",
#     block_time_seconds=12.0, explorer_url="https://etherscan.io",
# )
# ARBITRUM_CONFIG = ChainConfig(
#     chain_id=42161, name="Arbitrum One", native_token="ETH",
#     default_rpc_url="https://arb1.arbitrum.io/rpc",
#     block_time_seconds=0.25, explorer_url="https://arbiscan.io",
# )
# BSC_CONFIG = ChainConfig(
#     chain_id=56, name="BNB Smart Chain", native_token="BNB",
#     default_rpc_url="https://bsc-dataseed.binance.org",
#     block_time_seconds=3.0, explorer_url="https://bscscan.com",
# )
# BASE_CONFIG = ChainConfig(
#     chain_id=8453, name="Base", native_token="ETH",
#     default_rpc_url="https://mainnet.base.org",
#     block_time_seconds=2.0, explorer_url="https://basescan.org",
# )

CHAIN_CONFIGS = {
    "polygon": POLYGON_CONFIG,
}
