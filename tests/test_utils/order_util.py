#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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

import random
import time

from config import SIMULATOR_LAST_PRICES_TO_CHECK


async def fill_limit_or_stop_order(limit_or_stop_order, min_price, max_price):
    last_prices = []
    limit_or_stop_order.created_time = time.time()
    for i in range(0, SIMULATOR_LAST_PRICES_TO_CHECK):
        last_prices.insert(i, {})
        last_prices[i]["price"] = random.uniform(min_price, max_price)
        last_prices[i]["timestamp"] = time.time()

    limit_or_stop_order.last_prices = last_prices
    await limit_or_stop_order.update_order_status()


async def fill_market_order(market_order, price):
    last_prices = [{
        "price": price
    }]

    market_order.last_prices = last_prices
    await market_order.update_order_status()
