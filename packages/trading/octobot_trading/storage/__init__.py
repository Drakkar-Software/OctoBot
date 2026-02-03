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
#  License along with this library


from octobot_trading.storage import abstract_storage
from octobot_trading.storage.abstract_storage import (
    AbstractStorage,
)

from octobot_trading.storage import trades_storage
from octobot_trading.storage.trades_storage import (
    TradesStorage,
)

from octobot_trading.storage import orders_storage
from octobot_trading.storage.orders_storage import (
    OrdersStorage,
    get_order_trailing_profile_dict,
    restore_order_storage_origin_value,
)

from octobot_trading.storage import portfolio_storage
from octobot_trading.storage.portfolio_storage import (
    PortfolioStorage,
)

from octobot_trading.storage import candles_storage
from octobot_trading.storage.candles_storage import (
    CandlesStorage,
)

from octobot_trading.storage import transactions_storage
from octobot_trading.storage.transactions_storage import (
    TransactionsStorage,
)

from octobot_trading.storage import storage_manager
from octobot_trading.storage.storage_manager import (
    StorageManager,
)

from octobot_trading.storage import util
from octobot_trading.storage.util import (
    get_account_type_suffix_from_exchange_manager,
    get_account_type_suffix_from_run_metadata,
    get_account_type_suffix,
)

__all__ = [
    "AbstractStorage",
    "TradesStorage",
    "OrdersStorage",
    "get_order_trailing_profile_dict",
    "restore_order_storage_origin_value",
    "PortfolioStorage",
    "CandlesStorage",
    "TransactionsStorage",
    "StorageManager",
    "get_account_type_suffix_from_exchange_manager",
    "get_account_type_suffix_from_run_metadata",
    "get_account_type_suffix",
]
