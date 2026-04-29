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

import octobot_trading.personal_data.orders.triggers.base_trigger as base_trigger


class PriceTrigger(base_trigger.BaseTrigger):
    def __init__(
        self, on_trigger_callback: typing.Callable, on_trigger_callback_args: tuple,
        trigger_price: decimal.Decimal, trigger_above: bool
    ):
        super().__init__(on_trigger_callback, on_trigger_callback_args)
        self.trigger_price: decimal.Decimal = trigger_price
        self.trigger_above: bool = trigger_above

        self._exchange_manager = None
        self._symbol = None

    def triggers(self, current_price: decimal.Decimal) -> bool:
        return (
            (self.trigger_above and current_price >= self.trigger_price)
            or (
                not self.trigger_above and current_price <= self.trigger_price
            )
        )

    def update_from_other_trigger(self, other_trigger):
        self.trigger_price = other_trigger.trigger_price
        self.trigger_above = other_trigger.trigger_above

    def update(self, trigger_price=None, min_trigger_time=None, update_event=True, **kwargs):
        if self.trigger_price != trigger_price:
            self.trigger_price = trigger_price
            if update_event and self._exchange_manager is not None:
                # replace event
                self._clear_event()
                self._create_event(min_trigger_time)

    def clear(self):
        super().clear()
        self._clear_event()
        self._exchange_manager = None

    def _create_event(self, min_trigger_time: float):
        self._trigger_event = self._exchange_manager.exchange_symbols_data.\
            get_exchange_symbol_data(self._symbol).price_events_manager.\
            new_event(self.trigger_price, min_trigger_time, self.trigger_above, False)

    def _clear_event(self):
        if self._trigger_event is not None and self._exchange_manager is not None:
            self._exchange_manager.exchange_symbols_data. \
                get_exchange_symbol_data(self._symbol).price_events_manager.remove_event(self._trigger_event)

    def __str__(self):
        return f"{super().__str__()}: trigger_price={self.trigger_price}, trigger_above={self.trigger_above}"

    def _create_trigger_event(self, exchange_manager, symbol: str, min_trigger_time: float):
        self._exchange_manager = exchange_manager
        self._symbol = symbol
        self._create_event(min_trigger_time)