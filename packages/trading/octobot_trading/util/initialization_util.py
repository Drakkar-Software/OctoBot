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

import octobot_commons.tree as commons_tree


async def wait_for_topic_init(exchange_manager, timeout, topic, symbol=None, time_frame=None, symbols=None):
    if symbols:
        return await asyncio.gather(
            *[
                wait_for_topic_init(exchange_manager, timeout, topic, symbol=local_symbol, time_frame=None)
                for local_symbol in symbols
            ]
        )
    else:
        return await commons_tree.EventProvider.instance().wait_for_event(
            exchange_manager.bot_id,
            commons_tree.get_exchange_path(
                exchange_manager.exchange_name,
                topic,
                symbol=symbol,
                time_frame=time_frame
            ),
            timeout
        )
