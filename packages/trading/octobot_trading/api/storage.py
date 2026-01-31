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
import octobot_trading.storage as storage


async def clear_trades_storage_history(exchange_manager, flush=True):
    if exchange_manager.storage_manager.trades_storage:
        await exchange_manager.storage_manager.trades_storage.clear_history(flush=flush)
    if exchange_manager.exchange_personal_data.trades_manager:
        await exchange_manager.exchange_personal_data.trades_manager.reload_history(True)


async def clear_orders_storage_history(exchange_manager, flush=True):
    if exchange_manager.storage_manager.orders_storage:
        await exchange_manager.storage_manager.orders_storage.clear_history(flush=flush)


async def clear_transactions_storage_history(exchange_manager, flush=True):
    if exchange_manager.storage_manager.transactions_storage:
        await exchange_manager.storage_manager.transactions_storage.clear_history(flush=flush)


async def clear_portfolio_storage_history(exchange_manager, flush=True):
    if exchange_manager.storage_manager.portfolio_storage:
        await exchange_manager.storage_manager.portfolio_storage.clear_history(flush=flush)
    if exchange_manager.exchange_personal_data.portfolio_manager:
        await exchange_manager.exchange_personal_data.portfolio_manager.reset_history()
        # force flush now to save reset value in config
        await exchange_manager.storage_manager.portfolio_storage.flush()


async def clear_candles_storage_history(exchange_manager, flush=True):
    if exchange_manager.storage_manager.candles_storage:
        await exchange_manager.storage_manager.candles_storage.clear_history(flush=flush)


async def clear_database_storage_history(storage_class, database, flush=True):
    await storage_class.clear_database_history(database, flush=flush)


def get_account_type(is_future, is_margin, is_option, is_sandboxed, is_trader_simulated) -> str:
    return storage.get_account_type_suffix(is_future, is_margin, is_option, is_sandboxed, is_trader_simulated)


def get_account_type_from_run_metadata(run_metadata) -> str:
    return storage.get_account_type_suffix_from_run_metadata(run_metadata)


def get_account_type_from_exchange_manager(exchange_manager) -> str:
    return storage.get_account_type_suffix_from_exchange_manager(exchange_manager)
