#  Drakkar-Software OctoBot
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
import enum


class RebalanceDetails(enum.Enum):
    SELL_SOME = "SELL_SOME"
    BUY_MORE = "BUY_MORE"
    REMOVE = "REMOVE"
    ADD = "ADD"
    SWAP = "SWAP"
    FORCED_REBALANCE = "FORCED_REBALANCE"


class SynchronizationPolicy(enum.Enum):
    SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE = "sell_removed_index_coins_on_ratio_rebalance"
    SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE = "sell_removed_index_coins_as_soon_as_possible"
    SELL_REMOVED_DYNAMIC_INDEX_COINS_AS_SOON_AS_POSSIBLE = "sell_removed_dynamic_index_coins_as_soon_as_possible"


class DistributionKeys(enum.StrEnum):
    NAME = "name"
    VALUE = "value"
    PRICE = "price"

