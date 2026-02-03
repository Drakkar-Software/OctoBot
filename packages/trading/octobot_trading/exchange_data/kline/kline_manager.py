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
import octobot_commons.enums as enums
import octobot_commons.logging as logging

import octobot_trading.util as util


class KlineManager(util.Initializable):
    def __init__(self):  # Required for python development
        super().__init__()
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.kline: list[float] = []

    async def initialize_impl(self):
        self._reset_kline()

    def _reset_kline(self):
        self.kline = [math.nan] * len(enums.PriceIndexes)

    def _update_kline_key(self, kline_key, kline_update):
        try:
            if kline_update[kline_key] is not math.nan:
                self.kline[kline_key] = kline_update[kline_key]
        except KeyError:
            pass

    def _update_kline_init_only_key(self, kline_key, kline_update):
        try:
            if self.kline[kline_key] is math.nan:
                self.kline[kline_key] = kline_update[kline_key]
        except KeyError:
            pass

    def kline_update(self, kline):
        try:
            # test for new candle
            if self.kline[enums.PriceIndexes.IND_PRICE_TIME.value] != kline[enums.PriceIndexes.IND_PRICE_TIME.value]:
                self._reset_kline()

            self._update_kline_init_only_key(enums.PriceIndexes.IND_PRICE_TIME.value, kline)
            self._update_kline_init_only_key(enums.PriceIndexes.IND_PRICE_OPEN.value, kline)

            self._update_kline_key(enums.PriceIndexes.IND_PRICE_VOL.value, kline)
            self._update_kline_key(enums.PriceIndexes.IND_PRICE_CLOSE.value, kline)

            if self.kline[enums.PriceIndexes.IND_PRICE_HIGH.value] is math.nan or \
                    self.kline[enums.PriceIndexes.IND_PRICE_HIGH.value] < kline[enums.PriceIndexes.IND_PRICE_HIGH.value]:
                self._update_kline_key(enums.PriceIndexes.IND_PRICE_HIGH.value, kline)

            if self.kline[enums.PriceIndexes.IND_PRICE_LOW.value] is math.nan or \
                    self.kline[enums.PriceIndexes.IND_PRICE_LOW.value] > kline[enums.PriceIndexes.IND_PRICE_LOW.value]:
                self._update_kline_key(enums.PriceIndexes.IND_PRICE_LOW.value, kline)
        except TypeError as e:
            self.logger.error(f"Fail to update kline with {kline} : {e}")
