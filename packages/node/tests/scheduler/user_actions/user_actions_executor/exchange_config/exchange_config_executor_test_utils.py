#  Drakkar-Software OctoBot-Node
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import octobot_protocol.models as protocol_models

from ..account import account_executor_test_utils


WALLET_ADDRESS = account_executor_test_utils.WALLET_ADDRESS
wrap_configuration = account_executor_test_utils.wrap_configuration


def minimal_exchange_config(
    *,
    config_id: str,
    name: str = "binance-main",
    exchange: str = "binanceus",
    sandboxed: bool = False,
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id=config_id,
        name=name,
        exchange=exchange,
        sandboxed=sandboxed,
    )
