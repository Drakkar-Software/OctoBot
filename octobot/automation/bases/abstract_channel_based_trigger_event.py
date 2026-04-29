#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import abc
import asyncio
import typing

import async_channel
import octobot_trading.api as trading_api
import octobot.automation.bases.abstract_trigger_event as abstract_trigger_event
import octobot.errors as errors


class AbstractChannelBasedTriggerEvent(abstract_trigger_event.AbstractTriggerEvent, abc.ABC):
    def __init__(self):
        super(AbstractChannelBasedTriggerEvent, self).__init__()

        self.exchange: typing.Optional[str] = None
        self.exchange_id: typing.Optional[str] = None
        self.symbol: typing.Optional[str] = None


        # internal state
        self._trigger_event: asyncio.Event = asyncio.Event()
        self._consumers: list[async_channel.Consumer] = []
        self._registered_consumer: bool = False
        self._waiter_future: asyncio.Future = None # type: ignore

    async def register_consumers(self, exchange_id: str) -> list[async_channel.Consumer]:
        raise NotImplementedError(f"{self.__class__.__name__} must implement register_consumers")

    async def _register_exchange_channel_consumer(
        self,
        exchange: typing.Optional[str] = None,
        exchange_id: typing.Optional[str] = None,
        symbol: typing.Optional[str] = None,
    ):
        self._registered_consumer = True
        exchange = exchange or self.exchange
        exchange_id = exchange_id or self.exchange_id
        symbol = symbol or self.symbol
        if exchange_id and exchange:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_name_and_id(exchange, exchange_id)
        elif exchange_id:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        elif exchange:
            exchange_managers = trading_api.get_exchange_managers_from_exchange_name(exchange)
            if len(exchange_managers) != 1:
                raise ValueError(f"Expected 1 exchange manager for exchange {exchange}, got {len(exchange_managers)}")
            exchange_manager = exchange_managers[0]
        else:
            # register consumer for all exchanges
            for exchange_id in trading_api.get_exchange_ids():
                await self._register_exchange_channel_consumer(
                    exchange_id=exchange_id,
                )
            return
        if symbol:
            if symbol not in trading_api.get_trading_pairs(exchange_manager):
                raise ValueError(
                    f"Symbol {symbol} not found on {exchange}. "
                    f"Available symbols: {trading_api.get_trading_pairs(exchange_manager)}"
                )
        self._consumers.extend(await self.register_consumers(
            trading_api.get_exchange_manager_id(exchange_manager)
        ))

    async def stop(self):
        await super().stop()
        if self._waiter_future is not None and not self._waiter_future.done():
            self._waiter_future.cancel()
        for consumer in self._consumers:
            await consumer.stop()
        self._consumers = []
        self._registered_consumer = False

    async def check_initial_event(self):
        # implement if a check immediately after registering the consumer is necessary.
        # For example if the publication in registered channel can have been missed at the time of registration. 
        pass

    async def _get_next_event(self) -> typing.Optional[str]:
        if self.should_stop:
            raise errors.AutomationStopped
        self._waiter_future = asyncio.Future()
        if not self._registered_consumer:
            await self._register_exchange_channel_consumer()
            await self.check_initial_event()
        try:
            return await self._waiter_future
        except asyncio.CancelledError as err:
            if not self.should_stop:
                # stop to unregister consumers
                await self.stop()
            # clear_future was called
            raise errors.AutomationStopped from err

    def trigger(self, description: typing.Optional[str] = None):
        if self._waiter_future.done():
            self.logger.debug(f"Trigger {description} already done, skipping")
        else:
            self._waiter_future.set_result(description)

    def clear_future(self):
        if self._waiter_future is not None and not self._waiter_future.done():
            self._waiter_future.cancel()
