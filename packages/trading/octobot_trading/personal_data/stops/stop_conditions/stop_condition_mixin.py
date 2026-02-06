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

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges as trading_exchanges


class StopConditionMixin:
    def is_met(self, exchange_manager: "trading_exchanges.ExchangeManager") -> bool:
        raise NotImplementedError("is_met not implemented")

    def get_match_reason(self) -> str:
        raise NotImplementedError("get_match_reason is not implemented")
