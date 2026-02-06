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
import decimal
import typing

import octobot_commons.logging as commons_logging
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.errors as errors
import octobot_trading.personal_data.stops.stop_conditions as stop_conditions_import

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges as trading_exchanges

class StopWatcher:
    def __init__(
        self,
        stop_conditions: list[stop_conditions_import.StopConditionMixin],
        exchange_manager: "trading_exchanges.ExchangeManager",
        on_stop_callback: typing.Callable,
    ):
        self.triggered: bool = False
        self.holding_stop_conditions: list[stop_conditions_import.HoldingStopCondition] = [
            stop_condition 
            for stop_condition in stop_conditions if isinstance(stop_condition, stop_conditions_import.HoldingStopCondition)
        ]
        self.volatility_stop_conditions: list[stop_conditions_import.VolatilityStopCondition] = [
            stop_condition 
            for stop_condition in stop_conditions if isinstance(stop_condition, stop_conditions_import.VolatilityStopCondition)
        ]
        self._exchange_manager: "trading_exchanges.ExchangeManager" = exchange_manager
        self._on_stop_callback: typing.Callable = on_stop_callback
        self._stopped: bool = False

    async def start(self):
        self.triggered = False
        self._stopped = False
        if self.holding_stop_conditions:
            # ensure stop conditions are not met at initialization
            for holding_stop_condition in self.holding_stop_conditions:
                if holding_stop_condition.is_met(self._exchange_manager):
                    await self._on_stop_triggered(holding_stop_condition)
                    raise errors.StopTriggered(f"StopWatcher: {holding_stop_condition} is met at initialization.")
            await self._subscribe_to_exchange_balance(self._exchange_manager.id)
        self._get_logger().info(
            f"StopWatcher: started with {self.holding_stop_conditions + self.volatility_stop_conditions} "
            f"stop conditions for {self._exchange_manager.exchange_name}"
        )

    def should_subscribe_to_price_updates(self, symbol: str) -> bool:
        return any(
            volatility_stop_condition.symbol == symbol 
            for volatility_stop_condition in self.volatility_stop_conditions
        )

    async def on_new_price(self, symbol: str, price: decimal.Decimal):
        if self.triggered or self._stopped:
            # stop watcher is already triggered or stopped, nothing to do
            return
        for volatility_stop_condition in self.volatility_stop_conditions:
            if volatility_stop_condition.symbol == symbol:
                volatility_stop_condition.on_new_price(price)
            if volatility_stop_condition.is_met(self._exchange_manager):
                await self._on_stop_triggered(volatility_stop_condition)
                raise errors.StopTriggered(f"StopWatcher: {volatility_stop_condition} is met.")
   
    async def stop(self):
        self._stopped = True

    async def _subscribe_to_exchange_balance(self, exchange_id: str):
        await exchanges_channel.get_chan(trading_constants.BALANCE_CHANNEL, exchange_id).new_consumer(
            self._on_balance_update,
        )
        self._get_logger().info(
            f"StopWatcher: subscribing to {self._exchange_manager.exchange_name} balance. Stop condition: {self.holding_stop_conditions}"
        )

    async def _on_balance_update(self, exchange: str, exchange_id: str, balance):
        if self.triggered or self._stopped:
            # stop watcher is already triggered or stopped, nothing to do
            return
        for holding_stop_condition in self.holding_stop_conditions:
            if holding_stop_condition.is_met(self._exchange_manager):
                await self._on_stop_triggered(holding_stop_condition)
                return

    async def _on_stop_triggered(self, stop_condition: stop_conditions_import.StopConditionMixin):
        self._get_logger().info(f"StopWatcher: {stop_condition} is met.")
        await self._on_stop_callback(stop_condition)
        self.triggered = True

    def _get_logger(self):
        return commons_logging.get_logger(self.__class__.__name__)
