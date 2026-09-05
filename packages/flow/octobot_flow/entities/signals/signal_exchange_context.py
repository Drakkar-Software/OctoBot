#  Drakkar-Software OctoBot-Flow
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
#  OctoBot-Flow is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3.0 of the License, or (at
#  your option) any later version.

import dataclasses
import typing

import octobot_trading.enums as trading_enums


@dataclasses.dataclass(frozen=True)
class SignalExchangeContext:
    exchange_name: typing.Optional[str] = None
    exchange_type: typing.Optional[trading_enums.ExchangeTypes] = None
    reference_market: typing.Optional[str] = None
    ignore_exchange_key: bool = True
