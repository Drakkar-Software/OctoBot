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
import asyncio

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.personal_data.orders.order as order_class
import octobot_trading.personal_data.orders.decimal_order_adapter as decimal_order_adapter


class LimitOrder(order_class.Order):
    def __init__(self, trader, side=enums.TradeOrderSide.BUY):
        super().__init__(trader, side)
        self.limit_price_hit_event = None
        self.wait_for_hit_event_task = None
        self.trigger_above = self.side is enums.TradeOrderSide.SELL
        self.allow_instant_fill = constants.ALLOW_SIMULATED_ORDERS_INSTANT_FILL

    async def update_price_if_outdated(self):
        # price is outdated if it would trigger and instantly filled order with more than the allowed tolerance
        try:
            current_price = await self.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(self.symbol) \
                .prices_manager.get_mark_price(timeout=constants.CHAINED_ORDER_PRICE_FETCHING_TIMEOUT)
            self._update_limit_price_if_necessary(current_price)
        except asyncio.TimeoutError:
            # price can't be checked
            return

    def _update_limit_price_if_necessary(self, current_price):
        updated_price = self.origin_price
        if self.side is enums.TradeOrderSide.BUY:
            highest_accepted_buy_price = (
                current_price * (constants.ONE + constants.CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE)
            )
            if self.origin_price > highest_accepted_buy_price:
                # buy price is more than CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE % higher than the current price
                # => Reduce it to the highest allowed price
                updated_price = highest_accepted_buy_price
        if self.side is enums.TradeOrderSide.SELL:
            lowest_accepted_sell_price = (
                current_price * (constants.ONE - constants.CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE)
            )
            if self.origin_price < lowest_accepted_sell_price:
                # sell price is more than CHAINED_ORDERS_OUTDATED_PRICE_ALLOWANCE % lower than the current price
                # => Increase it to the current price
                updated_price = lowest_accepted_sell_price
        if self.origin_price != updated_price:
            symbol_market = self.exchange_manager.exchange.get_market_status(self.symbol, with_fixer=False)
            self.origin_price = decimal_order_adapter.decimal_adapt_price(symbol_market, updated_price)

    async def update_order_status(self, force_refresh=False):
        if self.is_active:
            if self.limit_price_hit_event is None:
                self._create_hit_event(self.creation_time)

            if self.wait_for_hit_event_task is None and self.limit_price_hit_event is not None:
                if self.limit_price_hit_event.is_set():
                    # order should be filled instantly
                    await self.on_fill()
                else:
                    # order will be filled when conditions are met
                    self._create_hit_task()

    def _on_origin_price_change(self, previous_price, price_time):
        super()._on_origin_price_change(previous_price, price_time)
        if previous_price is not constants.ZERO:
            # no need to reset events if previous price was 0 (unset)
            self._reset_events(price_time)

    def _create_hit_event(self, price_time):
        self.limit_price_hit_event = self.exchange_manager.exchange_symbols_data.\
            get_exchange_symbol_data(self.symbol).price_events_manager.\
            new_event(self.origin_price, price_time, self.trigger_above, self.allow_instant_fill)

    def _create_hit_task(self):
        if self.is_synchronization_enabled():
            self.wait_for_hit_event_task = asyncio.create_task(self.wait_for_price_hit())

    def _reset_events(self, price_time):
        """
        Reset events and tasks
        """
        self._clear_event_and_tasks()
        self._create_hit_event(price_time)
        self._create_hit_task()

    def _clear_event_and_tasks(self):
        if self.wait_for_hit_event_task is not None:
            if not self.limit_price_hit_event.is_set():
                self.wait_for_hit_event_task.cancel()
            self.wait_for_hit_event_task = None
        if self.limit_price_hit_event is not None:
            self.exchange_manager.exchange_symbols_data. \
                get_exchange_symbol_data(self.symbol).price_events_manager.remove_event(self.limit_price_hit_event)

    async def wait_for_price_hit(self):
        await asyncio.wait_for(self.limit_price_hit_event.wait(), timeout=None)
        await self.on_fill()

    def _should_instant_fill(self):
        open_price = self._get_open_price()
        filling_price = self.get_filling_price()
        if filling_price and open_price:
            if self.trigger_above:
                # instant fill if order price is lower or equal to market price: ex spot sell order
                return filling_price <= open_price
            # instant fill if order price is higher or equal to market price: ex spot buy order
            return filling_price >= open_price
        return False

    def _filled_maker_or_taker(self):
        return (
            enums.ExchangeConstantsMarketPropertyColumns.TAKER if self._should_instant_fill()
            else enums.ExchangeConstantsMarketPropertyColumns.MAKER
        ).value

    def on_fill_actions(self):
        self.taker_or_maker = self._filled_maker_or_taker()
        self.update_order_filled_values(self.origin_price)
        order_class.Order.on_fill_actions(self)

    def clear_active_order_elements(self):
        self._clear_event_and_tasks()
        order_class.Order.clear_active_order_elements(self)
