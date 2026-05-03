#  Drakkar-Software OctoBot-Private-Tentacles
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

import octobot_commons.enums
import octobot_commons.constants
import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums


class Bitfinex(exchanges.RestExchange):
    @classmethod
    def get_name(cls):
        return 'bitfinex'

    async def get_kline_price(self, symbol: str, time_frame: octobot_commons.enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list]:
        return (await self.get_symbol_prices(symbol, time_frame, limit=1))[-1:]

