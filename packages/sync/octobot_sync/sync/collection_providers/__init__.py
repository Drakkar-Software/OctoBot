#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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


import octobot_sync.sync.collection_providers.user_account_provider as user_account_provider_module
import octobot_sync.sync.collection_providers.user_strategy_provider as user_strategy_provider_module

AccountProvider = user_account_provider_module.AccountProvider
StrategyProvider = user_strategy_provider_module.StrategyProvider

__all__ = [
    "AccountProvider",
    "StrategyProvider",
]
