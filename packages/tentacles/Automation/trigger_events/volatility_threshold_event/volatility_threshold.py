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

import async_channel
import async_channel.enums as channel_enums
import octobot_commons.enums as commons_enums
import octobot_commons.configuration as configuration
import octobot_commons.constants as commons_constants
import octobot_commons.channels_name as channels_name
import octobot_commons.data_util as commons_data_util
import octobot.automation.bases.abstract_channel_based_trigger_event as abstract_channel_based_trigger_event
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot.errors as errors


@dataclasses.dataclass
class HistoricalMinAndMaxPrice:
    minute_ts: int
    min_price: decimal.Decimal
    max_price: decimal.Decimal

    def update(self, price: decimal.Decimal):
        self.min_price = min(self.min_price, price)
        self.max_price = max(self.max_price, price)


class VolatilityThresholdChecker:
    # extracted to be used in other tentacles if needed
    def __init__(
        self,
        symbol: str,
        period_in_minutes: float,
        max_allowed_positive_percentage_change: decimal.Decimal,
        max_allowed_negative_percentage_change: decimal.Decimal,
    ):
        self.symbol: str = symbol
        self.period_in_minutes: float = period_in_minutes
        self.max_allowed_positive_percentage_change = max_allowed_positive_percentage_change
        self.max_allowed_negative_percentage_change = max_allowed_negative_percentage_change
    
        self._historical_min_and_max_price_by_minute_ts: list[HistoricalMinAndMaxPrice] = []
        self._max_positive_ratio: decimal.Decimal = trading_constants.ZERO
        self._max_negative_ratio: decimal.Decimal = trading_constants.ZERO
        self._update_ratios()

    def _update_ratios(self):
        if self.max_allowed_positive_percentage_change:
            self._max_positive_ratio = trading_constants.ONE + self.max_allowed_positive_percentage_change / trading_constants.ONE_HUNDRED
        if self.max_allowed_negative_percentage_change:
            self._max_negative_ratio = trading_constants.ONE - self.max_allowed_negative_percentage_change / trading_constants.ONE_HUNDRED

    def validate_config(self):
        if not self.symbol or not self.period_in_minutes:
            raise errors.InvalidAutomationConfigError("symbol and period in minutes must be set", VolatilityThreshold.get_name())
        if self.max_allowed_positive_percentage_change <= trading_constants.ZERO:
            raise errors.InvalidAutomationConfigError("max allowed positive percentage change must be > 0", VolatilityThreshold.get_name())
        if self.max_allowed_negative_percentage_change <= trading_constants.ZERO:
            raise errors.InvalidAutomationConfigError("max allowed negative percentage change must be > 0", VolatilityThreshold.get_name())

        self._update_ratios()

    def _check_threshold(self) -> tuple[bool, typing.Optional[str]]:
        if len(self._historical_min_and_max_price_by_minute_ts) < 2:
            # need at least the current minute's price and the previous minute's price
            return False, None
        current_minute_price = self._historical_min_and_max_price_by_minute_ts[-1]
        if self.max_allowed_positive_percentage_change > trading_constants.ZERO:
            historical_average_max_price = commons_data_util.mean([
                historical_min_and_max_price.max_price 
                for historical_min_and_max_price in self._historical_min_and_max_price_by_minute_ts[:-1]
            ])
            if current_minute_price.max_price > historical_average_max_price * self._max_positive_ratio: # type: ignore
                return True, self._get_reason(historical_average_max_price, True)
        if self.max_allowed_negative_percentage_change > trading_constants.ZERO:
            historical_average_min_price = commons_data_util.mean([
                historical_min_and_max_price.min_price 
                for historical_min_and_max_price in self._historical_min_and_max_price_by_minute_ts[:-1]
            ])
            if current_minute_price.min_price < historical_average_min_price * self._max_negative_ratio: # type: ignore
                return True, self._get_reason(historical_average_min_price, False)
        return False, None

    def _get_reason(self, historical_average_price: decimal.Decimal, is_superior: bool) -> str:
        current_minute_price = self._historical_min_and_max_price_by_minute_ts[-1]
        current_value = current_minute_price.max_price if is_superior else current_minute_price.min_price
        return (
            f"{self.symbol} reference price of {float(current_value)} is {'above' if is_superior else 'bellow'} "
            f"the {self.period_in_minutes} minutes average {'high' if is_superior else 'low'} "
            f"value of {float(historical_average_price)} {'+' if is_superior else '-'}"
            f"{float(self.max_allowed_positive_percentage_change if is_superior else self.max_allowed_negative_percentage_change)}%."
        )

    def _update_last_historical_min_and_max_price(self, minute_ts: int, price: decimal.Decimal):
        if not self._historical_min_and_max_price_by_minute_ts or self._historical_min_and_max_price_by_minute_ts[-1].minute_ts != minute_ts:
            self._historical_min_and_max_price_by_minute_ts.append(HistoricalMinAndMaxPrice(minute_ts, price, price))
        else:
            self._historical_min_and_max_price_by_minute_ts[-1].update(price)

    def on_new_price(self, price: decimal.Decimal) -> tuple[bool, typing.Optional[str]]:
        current_time = time.time()
        current_minute_ts = int(current_time - (current_time // 60))
        self._update_last_historical_min_and_max_price(current_minute_ts, price)
        # ensure history doesn't grow forever
        # +1 because we need to keep the current minute's price in the history as well
        if len(self._historical_min_and_max_price_by_minute_ts) > (self.period_in_minutes + 1):
            self._historical_min_and_max_price_by_minute_ts.pop(0)
        return self._check_threshold()


class VolatilityThreshold(abstract_channel_based_trigger_event.AbstractChannelBasedTriggerEvent):
    EXCHANGE = "exchange"
    SYMBOL = "symbol"
    PERIOD_IN_MINUTES = "period_in_minutes"
    MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE = "max_allowed_positive_percentage_change"
    MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE = "max_allowed_negative_percentage_change"

    def __init__(self):
        super().__init__()
        # config
        self.volatility_threshold_checker: VolatilityThresholdChecker = VolatilityThresholdChecker(
            symbol=None, # type: ignore
            period_in_minutes=None, # type: ignore
            max_allowed_positive_percentage_change=None, # type: ignore
            max_allowed_negative_percentage_change=None, # type: ignore
        )

    @staticmethod
    def get_description() -> str:
        return (
            "Will trigger when the price of the given symbol reaches a certain percentage change from the average price of the given period." \
            "Example: a Period of 1440 and a Max allowed positive percentage change of 1 will trigger the automation if the price of ETH/USDT reaches 1% above the average price by minutes over the past 1440 minutes."
        )

    def get_user_inputs(
        self, UI: configuration.UserInputFactory, inputs: dict, step_name: str
    ) -> dict:
        return {
            self.EXCHANGE: UI.user_input(
                self.EXCHANGE, commons_enums.UserInputTypes.TEXT, "binance", inputs,
                title="Exchange: exchange to watch price on. Example: binance. Leave empty to enable on all exchanges.",
                parent_input_name=step_name,
                other_schema_values={"minLength": 1}
            ),
            self.SYMBOL: UI.user_input(
                self.SYMBOL, commons_enums.UserInputTypes.TEXT, "BTC/USDT", inputs,
                title="Symbol: symbol to watch price on. Example: ETH/USDT. The symbol should be a configured trading pair of the exchange.",
                parent_input_name=step_name,
                other_schema_values={"minLength": 3, "pattern": commons_constants.TRADING_SYMBOL_REGEX}
            ),
            self.PERIOD_IN_MINUTES: UI.user_input(
                self.PERIOD_IN_MINUTES, commons_enums.UserInputTypes.FLOAT, 60, inputs,
                title="Period in minutes: period to watch price on. Example: 1440 for 1 day",
                parent_input_name=step_name,
                min_val=0,
                other_schema_values={"exclusiveMinimum": True}
            ),
            self.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE: UI.user_input(
                self.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE, commons_enums.UserInputTypes.FLOAT, 1.0, inputs,
                title="Max allowed positive percentage change. Leave 0 to disable. Example: 1 for 1%",
                parent_input_name=step_name,
                min_val=0,
            ),
            self.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE: UI.user_input(
                self.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE, commons_enums.UserInputTypes.FLOAT, 1.0, inputs,
                title="Max allowed negative percentage change. Leave 0 to disable. Example: 1 for -1%",
                parent_input_name=step_name,
                min_val=0,
            ),
        }

    def apply_config(self, config: dict) -> None:
        self.clear_future()
        self.exchange = config[self.EXCHANGE] or None
        self.symbol = config[self.SYMBOL]
        self.volatility_threshold_checker.symbol = self.symbol # type: ignore
        self.volatility_threshold_checker.period_in_minutes = config[self.PERIOD_IN_MINUTES]
        self.volatility_threshold_checker.max_allowed_positive_percentage_change = decimal.Decimal(str(
            config[self.MAX_ALLOWED_POSITIVE_PERCENTAGE_CHANGE]
        ))
        self.volatility_threshold_checker.max_allowed_negative_percentage_change = decimal.Decimal(str(
            config[self.MAX_ALLOWED_NEGATIVE_PERCENTAGE_CHANGE]
        ))
        self.volatility_threshold_checker.validate_config()

    async def register_consumers(self, exchange_id: str) -> list[async_channel.Consumer]:
        return [
            await exchanges_channel.get_chan(
                channels_name.OctoBotTradingChannelsName.MARK_PRICE_CHANNEL.value, exchange_id
            ).new_consumer(
                self.mark_price_callback,
                priority_level=channel_enums.ChannelConsumerPriorityLevels.HIGH.value,
                symbol=self.volatility_threshold_checker.symbol,
            )
        ]

    async def mark_price_callback(
        self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
    ):
        if self.should_stop:
            # do not go any further if the action has been stopped
            return
        is_threshold_met, reason = self.volatility_threshold_checker.on_new_price(decimal.Decimal(str(mark_price)))
        if is_threshold_met:
            self.logger.info(f"Volatility threshold met for {exchange}: {reason}")
            self.trigger(description=reason)
