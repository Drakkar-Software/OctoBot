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

DEFAULT_ORDER_SYMBOL = "BTC/USDT"
DEFAULT_SYMBOL_QUANTITY = 10
DEFAULT_MARKET_QUANTITY = 1000


def check_created_transaction(exchange_manager, closed_quantity, cumulated_closed_quantity):
    transaction = get_latest_transaction(exchange_manager)
    assert transaction.closed_quantity == closed_quantity
    assert transaction.cumulated_closed_quantity == cumulated_closed_quantity


def get_latest_transaction(exchange_manager):
    transactions = exchange_manager.exchange_personal_data.transactions_manager.transactions
    return list(transactions.values())[-1] if transactions else None
