#  Drakkar-Software OctoBot-Private-Tentacles
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

import async_channel.enums as channel_enums
import octobot_commons.channels_name as channels_name

import octobot_trading.enums as trading_enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools


class SpotRestExchangeTests:
    SUBSCRIBED_CHANNELS = [channels_name.OctoBotTradingChannelsName.BALANCE_CHANNEL.value,
                           channels_name.OctoBotTradingChannelsName.TRADES_CHANNEL.value,
                           channels_name.OctoBotTradingChannelsName.ORDERS_CHANNEL.value]

    def __init__(self, exchange_name, config):
        self.config = config
        self.exchange_name = exchange_name

        self.exchange_manager_instance = None

        self.channel_callbacks_triggered = {}
        self.expected_crypto_in_balance = []

    async def initialize(self):
        self.exchange_manager_instance = await exchanges_test_tools.create_test_exchange_manager(
            config=self.config, exchange_name=self.exchange_name,
            rest_only=True, is_spot_only=True, is_sandboxed=True, ignore_exchange_config=False)
        await self.exchange_manager_instance.trader.initialize()

    async def run(self, symbol):
        await self.subscribe_personal_channels()
        await self.exchange_manager_instance.trader.cancel_all_open_orders()
        await self.test_orders(symbol)

    async def stop(self):
        await exchanges_test_tools.stop_test_exchange_manager(self.exchange_manager_instance)

    async def test_orders(self, symbol):
        mark_price = await self.exchange_manager_instance.exchange_symbols_data.get_exchange_symbol_data(symbol) \
            .prices_manager.get_mark_price(timeout=60)
        await self._create_order(symbol,
                                 trading_enums.TraderOrderType.SELL_LIMIT,
                                 mark_price * decimal.Decimal("1.1"),
                                 decimal.Decimal("1.001"),
                                 mark_price * decimal.Decimal("1.1"))
        await asyncio.sleep(7)
        assert (await self._get_exchange_orders_count(symbol)) == 1
        open_orders = self._get_orders_manager_open_orders(symbol)
        assert len(open_orders) == 1
        await self.exchange_manager_instance.trader.cancel_order_with_id(open_orders[-1].order_id)
        await asyncio.sleep(7)
        assert (await self._get_exchange_orders_count(symbol)) == 0
        open_orders = self._get_orders_manager_open_orders(symbol)
        assert len(open_orders) == 0

    async def _get_exchange_orders_count(self, symbol):
        return len(await self.exchange_manager_instance.exchange.get_open_orders(symbol=symbol))

    def _get_orders_manager_open_orders(self, symbol):
        return self.exchange_manager_instance.exchange_personal_data.orders_manager.get_open_orders(symbol)

    async def test_all_callback_triggered(self):
        for channel in self.SUBSCRIBED_CHANNELS:
            assert self.channel_callbacks_triggered.get(channel, False)

    async def _create_order(self, symbol, order_type, current_price, quantity, limit_price):
        current_order = trading_personal_data.create_order_instance(trader=self.exchange_manager_instance.trader,
                                                                    order_type=order_type,
                                                                    symbol=symbol,
                                                                    current_price=current_price,
                                                                    quantity=quantity,
                                                                    price=limit_price)
        await self.exchange_manager_instance.trader.create_order(current_order)

    async def subscribe_personal_channels(self):
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.BALANCE_CHANNEL.value,
                                         self.exchange_manager_instance.id).new_consumer(
            self._balance_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.TRADES_CHANNEL.value,
                                         self.exchange_manager_instance.id).new_consumer(
            self._trades_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
        )
        await exchanges_channel.get_chan(channels_name.OctoBotTradingChannelsName.ORDERS_CHANNEL.value,
                                         self.exchange_manager_instance.id).new_consumer(
            self._orders_callback, priority_level=channel_enums.ChannelConsumerPriorityLevels.MEDIUM.value
        )

    def _check_balance_crypto(self, balance):
        for crypto in self.expected_crypto_in_balance:
            assert crypto in balance

    async def _balance_callback(self, exchange: str, exchange_id: str, balance):
        self.channel_callbacks_triggered[channels_name.OctoBotTradingChannelsName.BALANCE_CHANNEL.value] = True
        self._check_balance_crypto(balance)

    async def _trades_callback(
            self,
            exchange: str,
            exchange_id: str,
            cryptocurrency: str,
            symbol: str,
            trade: dict,
            old_trade: bool,
    ):
        self.channel_callbacks_triggered[channels_name.OctoBotTradingChannelsName.TRADES_CHANNEL.value] = True

    async def _orders_callback(
            self,
            exchange: str,
            exchange_id: str,
            cryptocurrency: str,
            symbol: str,
            order: dict,
            update_type: str,
            is_from_bot: bool,
    ):
        self.channel_callbacks_triggered[channels_name.OctoBotTradingChannelsName.ORDERS_CHANNEL.value] = True
