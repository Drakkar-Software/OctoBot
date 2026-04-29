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
import math
import typing
import octobot_commons.logging as logging

import octobot_trading.enums as enums
import octobot_trading.util as util


class TickerManager(util.Initializable):
    def __init__(self):
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.ticker: dict[str, typing.Any] = {}
        self.mini_ticker: dict[str, typing.Any] = {}
        self.reset_ticker()
        self.reset_mini_ticker()

    async def initialize_impl(self):
        self.reset_ticker()
        self.reset_mini_ticker()

    def reset_mini_ticker(self):
        self.mini_ticker = {
            enums.ExchangeConstantsMiniTickerColumns.HIGH_PRICE.value: math.nan,
            enums.ExchangeConstantsMiniTickerColumns.LOW_PRICE.value: math.nan,
            enums.ExchangeConstantsMiniTickerColumns.OPEN_PRICE.value: math.nan,
            enums.ExchangeConstantsMiniTickerColumns.CLOSE_PRICE.value: math.nan,
            enums.ExchangeConstantsMiniTickerColumns.VOLUME.value: math.nan,
            enums.ExchangeConstantsMiniTickerColumns.TIMESTAMP.value: 0
        }

    def reset_ticker(self):
        self.ticker = {
            enums.ExchangeConstantsTickersColumns.ASK.value: math.nan,
            enums.ExchangeConstantsTickersColumns.ASK_VOLUME.value: math.nan,
            enums.ExchangeConstantsTickersColumns.BID.value: math.nan,
            enums.ExchangeConstantsTickersColumns.BID_VOLUME.value: math.nan,
            enums.ExchangeConstantsTickersColumns.OPEN.value: math.nan,
            enums.ExchangeConstantsTickersColumns.LOW.value: math.nan,
            enums.ExchangeConstantsTickersColumns.HIGH.value: math.nan,
            enums.ExchangeConstantsTickersColumns.CLOSE.value: math.nan,
            enums.ExchangeConstantsTickersColumns.LAST.value: math.nan,
            enums.ExchangeConstantsTickersColumns.AVERAGE.value: math.nan,
            enums.ExchangeConstantsTickersColumns.SYMBOL.value: math.nan,
            enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: math.nan,
            enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: math.nan,
            enums.ExchangeConstantsTickersColumns.TIMESTAMP.value: 0,
            enums.ExchangeConstantsTickersColumns.VWAP.value: math.nan
        }

    def ticker_update(self, ticker):
        ticker_update = {
            key: val
            for key, val in ticker.items()
            if val
        }
        self.ticker.update(ticker_update)

    def mini_ticker_update(self, mini_ticker):
        self.mini_ticker.update(mini_ticker)
