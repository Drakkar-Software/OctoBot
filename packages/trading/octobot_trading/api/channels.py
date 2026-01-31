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
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.exchange_data as exchange_data
import octobot_trading.personal_data as personal_data


async def subscribe_to_ohlcv_channel(callback, exchange_id):
    await _subscribe_to_channel(callback, exchange_id, exchange_data.OHLCVChannel)


async def subscribe_to_trades_channel(callback, exchange_id):
    await _subscribe_to_channel(callback, exchange_id, personal_data.TradesChannel)


async def subscribe_to_order_channel(callback, exchange_id):
    await _subscribe_to_channel(callback, exchange_id, personal_data.OrdersChannel)


async def _subscribe_to_channel(callback, exchange_id, channel):
    channel = exchange_channel.get_chan(channel.get_name(), exchange_id)
    await channel.new_consumer(callback)
