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
import functools
import typing

import octobot_commons.tentacles_management as tentacles_management
import octobot_trading.lending_protocols.abstract_lending_protocol as abstract_lending_protocol

if typing.TYPE_CHECKING:
    import octobot_trading.blockchain_wallets.blockchain_wallet as blockchain_wallet


@functools.lru_cache(maxsize=1)
def get_lending_protocol_class_by_protocol() -> dict[
    str, type[abstract_lending_protocol.AbstractLendingProtocol]
]:
    """
    Discover all AbstractLendingProtocol subclasses and map them by PROTOCOL name.
    Cached to avoid re-scanning tentacles for each protocol creation.
    Mirrors blockchain_wallet_factory.get_blockchain_wallet_class_by_blockchain().
    """
    return {
        protocol_class.PROTOCOL: protocol_class
        for protocol_class in tentacles_management.get_all_classes_from_parent(
            abstract_lending_protocol.AbstractLendingProtocol
        )
        if protocol_class.PROTOCOL is not None
    }


def create_lending_protocol(
    protocol_name: str,
    wallet: "blockchain_wallet.BlockchainWallet",
) -> abstract_lending_protocol.AbstractLendingProtocol:
    """
    Create a lending protocol instance of the given type.
    :param protocol_name: the protocol identifier (e.g., "aave_v3_polygon")
    :param wallet: the blockchain wallet to use for on-chain interactions
    :return: the created lending protocol instance
    :raises ValueError: if the protocol is not supported
    """
    try:
        protocol_class = get_lending_protocol_class_by_protocol()[protocol_name]
        return protocol_class(wallet)
    except KeyError as err:
        available = list(get_lending_protocol_class_by_protocol().keys())
        raise ValueError(
            f"Lending protocol '{protocol_name}' not supported. "
            f"Available protocols: {available}"
        ) from err
