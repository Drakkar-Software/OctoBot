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
import dataclasses
import decimal
import time
import typing

import octobot_commons.data_util as commons_data_util
import octobot_commons.dataclasses as commons_dataclasses
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data.stops.stop_conditions.stop_condition_mixin as stop_condition_mixin


if typing.TYPE_CHECKING:
    import octobot_trading.exchanges as trading_exchanges

@dataclasses.dataclass
class HistoricalMinAndMaxPrice:
    minute_ts: int
    min_price: decimal.Decimal
    max_price: decimal.Decimal

    def update(self, price: decimal.Decimal):
        self.min_price = min(self.min_price, price)
        self.max_price = max(self.max_price, price)


@dataclasses.dataclass
class VolatilityStopCondition(commons_dataclasses.FlexibleDataclass, stop_condition_mixin.StopConditionMixin):
    symbol: str
    period_in_minutes: int
    max_allowed_positive_percentage_change: decimal.Decimal
    max_allowed_negative_percentage_change: decimal.Decimal

    _historical_min_and_max_price_by_minute_ts: list[HistoricalMinAndMaxPrice] = dataclasses.field(default_factory=list, repr=False)
    _max_positive_ratio: decimal.Decimal = dataclasses.field(default=trading_constants.ONE, repr=False)
    _max_negative_ratio: decimal.Decimal = dataclasses.field(default=trading_constants.ONE, repr=False)
    _last_match_reason: str = ""

    def __post_init__(self):
        self.max_allowed_positive_percentage_change = decimal.Decimal(str(self.max_allowed_positive_percentage_change))
        self.max_allowed_negative_percentage_change = decimal.Decimal(str(self.max_allowed_negative_percentage_change))
        # avoid recomputing the ratio on each call
        self._max_positive_ratio = trading_constants.ONE + self.max_allowed_positive_percentage_change / decimal.Decimal(100)
        self._max_negative_ratio = trading_constants.ONE - self.max_allowed_negative_percentage_change / decimal.Decimal(100)

    def is_met(self, exchange_manager: "trading_exchanges.ExchangeManager") -> bool:
        if len(self._historical_min_and_max_price_by_minute_ts) < 2:
            # need at least the current minute's price and the previous minute's price
            return False
        current_minute_price = self._historical_min_and_max_price_by_minute_ts[-1]
        if self.max_allowed_positive_percentage_change > trading_constants.ZERO:
            historical_average_max_price = commons_data_util.mean([
                historical_min_and_max_price.max_price 
                for historical_min_and_max_price in self._historical_min_and_max_price_by_minute_ts[:-1]
            ])
            if current_minute_price.max_price > historical_average_max_price * self._max_positive_ratio: # type: ignore
                self._last_match_reason = self._get_reason(historical_average_max_price, True)
                return True
        if self.max_allowed_negative_percentage_change > trading_constants.ZERO:
            historical_average_min_price = commons_data_util.mean([
                historical_min_and_max_price.min_price 
                for historical_min_and_max_price in self._historical_min_and_max_price_by_minute_ts[:-1]
            ])
            if current_minute_price.min_price < historical_average_min_price * self._max_negative_ratio: # type: ignore
                self._last_match_reason = self._get_reason(historical_average_min_price, False)
                return True
        return False

    def _get_reason(self, historical_average_price: decimal.Decimal, is_superior: bool) -> str:
        current_minute_price = self._historical_min_and_max_price_by_minute_ts[-1]
        current_value = current_minute_price.max_price if is_superior else current_minute_price.min_price
        return (
            f"{self.symbol} reference price of {float(current_value)} is {'above' if is_superior else 'bellow'} "
            f"the {self.period_in_minutes} minutes average {'high' if is_superior else 'low'} "
            f"value of {float(historical_average_price)} {'+' if is_superior else '-'}"
            f"{float(self.max_allowed_positive_percentage_change if is_superior else self.max_allowed_negative_percentage_change)}%."
        )

    def get_match_reason(self) -> str:
        return self._last_match_reason

    def on_new_price(self, price: decimal.Decimal):
        current_time = time.time()
        current_minute_ts = int(current_time - (current_time // 60))
        self._update_last_historical_min_and_max_price(current_minute_ts, price)
        # ensure history doesn't grow forever
        # +1 because we need to keep the current minute's price in the history as well
        if len(self._historical_min_and_max_price_by_minute_ts) > (self.period_in_minutes + 1):
            self._historical_min_and_max_price_by_minute_ts.pop(0)

    def _update_last_historical_min_and_max_price(self, minute_ts: int, price: decimal.Decimal):
        if not self._historical_min_and_max_price_by_minute_ts or self._historical_min_and_max_price_by_minute_ts[-1].minute_ts != minute_ts:
            self._historical_min_and_max_price_by_minute_ts.append(HistoricalMinAndMaxPrice(minute_ts, price, price))
        else:
            self._historical_min_and_max_price_by_minute_ts[-1].update(price)
