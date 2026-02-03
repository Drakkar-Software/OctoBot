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

import octobot_trading.exchanges as exchanges
import octobot_trading.enums as trading_enums
import octobot_commons.enums as commons_enums


class WavesExchange(exchanges.RestExchange):
    DESCRIPTION = ""
    FIX_MARKET_STATUS = True
    DUMP_INCOMPLETE_LAST_CANDLE = True  # set True in tentacle when the exchange can return incomplete last candles

    @classmethod
    def get_name(cls):
        return 'wavesexchange'

    def get_adapter_class(self):
        return WavesCCXTAdapter

    async def get_symbol_prices(self, symbol: str, time_frame: commons_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        # without limit is not supported
        if limit is not None:
            # account for potentially dumped candle
            limit += 1
        return await super().get_symbol_prices(symbol, time_frame, limit=limit, **kwargs)


class WavesCCXTAdapter(exchanges.CCXTAdapter):

    def fix_ticker(self, raw, **kwargs):
        fixed = super().fix_ticker(raw, **kwargs)
        fixed[trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
            fixed.get(trading_enums.ExchangeConstantsTickersColumns.TIMESTAMP.value) or self.connector.client.seconds()
        return fixed
