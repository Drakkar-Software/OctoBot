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


import octobot_commons.singleton.singleton_class as singleton_class
import octobot_sync.constants as sync_constants
import octobot_protocol.models as protocol_models
import octobot_sync.enums as sync_enums

import octobot_sync.sync.collection_backend.single_item_local_collection_provider as single_item_provider


class AccountTradingProvider(
    single_item_provider.SingleItemLocalCollectionProvider[protocol_models.AccountTradingState],
    singleton_class.Singleton,
):
    """
    Singleton provider for per-account trading state.

    Each account is stored in its own encrypted file under
    ``<collection>/<wallet>/<account_id>.json``.
    """
    COLLECTION = sync_enums.Collections.USER_ACCOUNTS_TRADING.value
    STATE_VERSION = sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION
    STATE_CLASS = protocol_models.AccountTradingState
