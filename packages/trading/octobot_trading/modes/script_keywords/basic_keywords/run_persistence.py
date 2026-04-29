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

import octobot_commons.enums as commons_enums
import octobot_commons.databases as commons_databases


def set_plot_orders(ctx, value):
    ctx.plot_orders = value


async def disable_candles_plot(ctx, exchange_manager=None):
    storage = (exchange_manager or ctx.exchange_manager).storage_manager.candles_storage
    await storage.enable(False)
    await storage.clear_history()


async def clear_orders_cache(writer):
    await _clear_table(writer, commons_enums.DBTables.ORDERS.value)
    await writer.clear()


async def clear_symbol_plot_cache(writer):
    await _clear_table(writer, commons_enums.DBTables.CACHE_SOURCE.value)
    await writer.clear()


async def _clear_table(writer, table, flush=True):
    await writer.delete(table, None)
    if flush:
        await writer.flush()


def get_shared_element(key):
    return commons_databases.GlobalSharedMemoryStorage.instance()[key]


def set_shared_element(key, element):
    commons_databases.GlobalSharedMemoryStorage.instance()[key] = element
