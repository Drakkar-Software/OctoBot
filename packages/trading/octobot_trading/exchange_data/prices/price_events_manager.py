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
import decimal
import typing

import octobot_commons.logging as logging
from octobot_trading.enums import ExchangeConstantsOrderColumns as ECOC


class PriceEventsManager:
    """
    Manage price events for a specific price and timestamp
    Mainly used for updating Order status
    """

    """
    The price event index from a price event tuple
    """
    PRICE_EVENT_INDEX = 2
    PRICE_KEY = "price"
    TIME_KEY = "time"
    MAX_LAST_RECENT_PRICES = 50

    def __init__(self):
        self.logger: logging.BotLogger = logging.get_logger(self.__class__.__name__)
        self.events: list[tuple[decimal.Decimal, int, asyncio.Event, bool]] = []
        self._last_recent_prices: list[dict[str, typing.Union[decimal.Decimal, int]]] = []

    def stop(self):
        self.reset()

    def reset(self):
        """
        Reset price events
        """
        self.clear_recent_prices()
        self.events.clear()

    def get_min_and_max_prices(self) -> (float, float):
        if len(self._last_recent_prices) < 2:
            raise IndexError("Not enough data")
        prices = sorted([element[self.PRICE_KEY] for element in self._last_recent_prices])
        return prices[0], prices[-1]

    def handle_recent_trades(self, recent_trades):
        """
        Handle new recent trades prices
        :param recent_trades: prices to check
        """
        # reset recent prices on new recent trades
        self.clear_recent_prices()
        for recent_trade in recent_trades:
            price = decimal.Decimal(str(recent_trade[ECOC.PRICE.value]))
            timestamp = recent_trade[ECOC.TIMESTAMP.value]
            try:
                self._add_recent_price(price, timestamp)
                for event_to_set in self._check_events(price, timestamp):
                    self._remove_and_set_event(event_to_set)
            except KeyError:
                self.logger.error("Error when checking price events with recent trades data")

    def handle_price(self, price, timestamp):
        """
        Handle new simple price with timestamp
        :param price: the price to check
        :param timestamp: the timestamp to check
        """
        self._add_recent_price(price, timestamp)
        for event_to_set in self._check_events(price, timestamp):
            self._remove_and_set_event(event_to_set)

    def clear_recent_prices(self):
        self._last_recent_prices = []

    def _add_recent_price(self, price, timestamp):
        self._last_recent_prices.append({
            self.PRICE_KEY: price,
            self.TIME_KEY: timestamp
        })
        self._ensure_last_prices_length()

    def _ensure_last_prices_length(self):
        if len(self._last_recent_prices) > self.MAX_LAST_RECENT_PRICES:
            # only take the most recent prices
            self._last_recent_prices = self._last_recent_prices[self.MAX_LAST_RECENT_PRICES // 2:]

    def new_event(self, price, timestamp, trigger_above, allow_instant_fill=True):
        """
        Create a new event at price and timestamp.
        This event can already be set should it be instantly triggered.
        Otherwise it will be set once the required price conditions are met
        :param price: the trigger price
        :param timestamp: the timestamp to wait for
        :param trigger_above: True if waiting for an upper price
        :param allow_instant_fill: True if recent prices should be checked to fill this event
        :return: the price event
        """
        price_event_tuple = _new_price_event(price, timestamp, trigger_above)
        if allow_instant_fill and self._is_triggered_by_last_recent_prices(price, timestamp, trigger_above):
            # don't add to self.events an event that is already set
            price_event_tuple[PriceEventsManager.PRICE_EVENT_INDEX].set()
        else:
            # this event will be set when conditions are met
            self.events.append(price_event_tuple)
        return price_event_tuple[PriceEventsManager.PRICE_EVENT_INDEX]

    def _is_triggered_by_last_recent_prices(self, price, timestamp, trigger_above):
        """
        Check if the give price and time would be instantly triggered by last recent trades
        :param price: the trigger price
        :param timestamp: the timestamp to wait for
        :param trigger_above: True if waiting for an upper price
        :return: True if it would be triggered
        """
        for recent_price in self._last_recent_prices:
            trade_price = recent_price[self.PRICE_KEY]
            if timestamp <= recent_price[self.TIME_KEY] and (
                (trigger_above and price <= trade_price) or
                (not trigger_above and price >= trade_price)
            ):
                return True
        return False

    def remove_event(self, event_to_remove):
        """
        Public method that calls _remove_event()
        :param event_to_remove: the event to remove
        """
        return self._remove_event(event_to_remove)

    def _remove_and_set_event(self, event_to_set):
        """
        Set the event and remove it from event list
        :param event_to_set: the event to set
        :return: the event index removed from event list
        """
        event_to_set.set()
        return self._remove_event(event_to_set)

    def _remove_event(self, event_to_remove):
        """
        Remove the event from events list
        :param event_to_remove: the event to remove
        """
        for price_event_data in self.events:
            if event_to_remove in price_event_data:
                return self.events.remove(price_event_data)

    def _check_events(self, price, timestamp):
        """
        Check for each price, timestamp pair event if it should be triggered
        :param price: the price used to check
        :param timestamp: the timestamp used to check
        :return: the event list that match
        """
        return [
            event
            for event_price, event_timestamp, event, trigger_above in self.events
            if event_timestamp <= timestamp and
            (
                (trigger_above and event_price <= price) or
                (not trigger_above and event_price >= price)
            )
        ]


def _new_price_event(price, timestamp, trigger_above):
    """
    Create a new price event item
    :param price: the price condition
    :param timestamp: the timestamp condition
    :param trigger_above: True if waiting for an upper price
    :return: a tuple to be added into events list
    """
    return price, timestamp, asyncio.Event(), trigger_above
